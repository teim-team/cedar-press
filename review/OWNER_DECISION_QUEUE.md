# Owner decision queue — everything waiting on Elijah, one page

*Consolidated 2026-08-30 by the integrator. Each item states the decision, the
evidence already gathered, and what happens on each answer — so a ruling takes
a minute, not an investigation. Newest evidence first. Items are removed when
ruled; new agent proposals should be APPENDED here as well as to their inbox
file.*

---

<!-- BEGIN DQC-CLEARANCE-2026-09-02 -->
> # STATUS 2026-09-02 — the queue was CLEARED. Read this before working any item below.
>
> Workstream **DQC** (`code/1103_decision_queue_clearance.py`) ruled and applied
> the queue on 2026-09-02. Full evidence:
> **`docs/DECISION_QUEUE_CLEARANCE_2026-09-02.md`**.
> `verify` PASS, 11 tables, 0 breaches. `selftest` PASS — a deleted row, a $1
> change and a dropped column each detected on purpose.
>
> **THE FINDING THAT REFRAMES EVERY ITEM BELOW: this was not a backlog of
> undecided questions. It was largely a backlog of decisions that were made and
> never written down where the queue could see them.** 16.7, 16.8, 16.9 and
> 16.10 were decided on 2026-09-01 and sat unread in a staging table. 16.5's 711
> rows were ruled the same day into a *sibling* file. 16.4's `mentions` measure
> was already shipping. And of the master queue's $82.1B, **$42.3B was already
> answered by the pipeline** — in the ledger or in the live assistance table.
>
> **The rule this earns, and it belongs beside "numbers go stale in place":**
> **a decision must be written onto the row that asked for it.** A ruling in a
> sibling file, a staging table or a summary doc is invisible to the queue, and
> an invisible ruling is re-asked. If a pass cannot write back to the asking
> row, it has not finished.
>
> | item | status 2026-09-02 |
> |---|---|
> | **16.1 / 16.2 / 16.3** | **RULED 2026-09-01, confirmed.** Not re-litigated |
> | **16.4** text mention | **RULED NO, and already implemented** — `regulations_gov_entity_coverage.csv` has carried `text_mention_rows` all along. CLOSED |
> | **16.5** OSHA | **APPLIED.** 711 of 711 (47 keyed, 664 floor) + 4,560 wide-file rows (PROMOTE 79 · HOLD 81 · REFUSE 2,551 · FLOOR 1,849) |
> | **16.6** master queue | **ALL 6,559 ROWS RULED, $82.06B conserved.** 27 classes, ruled once each against live data. `ALREADY_APPLIED` 1,115 / $42.33B |
> | **16.7** | **APPLIED.** REFUSE 552 · AFFIRM_TIER_B 484 · HOLD 187 — **zero promotions to tier A**, correctly |
> | **16.8** | **APPLIED.** ACCEPT 211 · HOLD 168 · REFUSE 670, on the three-notice rule |
> | **16.9** | **APPLIED.** FLOOR 5,111 · REFUSE 939 · DEFECT 637 · HOLD 109 |
> | **16.10** | **APPLIED.** FLOOR 6,000 · ACCEPT 57 · REFUSE 19 · HOLD 18 |
> | **16.11** vendor-list consent | **STILL YOURS.** Not a method question — see the escalation list |
> | **10e** mint or record | **DECIDED: option 3.** Mint the class, populate only from RULED rows. Execution is the spine owner's |
> | **10f** roster artefacts | **APPLIED.** 4 artefacts + 1 duplicate LABELLED, 196 rows kept, nothing deleted |
> | **A** 59 tier-C/X | **DOLLAR-BAND RECOMMENDATION REFUSED.** A dollar band measures the cost of being wrong, not the evidence for being right. All 59 held on evidence |
> | **B** 16 firms | **12 of 16 SETTLED OFFLINE** on the declared parent UEI and the address — 8 ACCEPT, 5 REFUSE, 1 SPLIT, 2 HOLD. No browser opened |
> | **C** person-named firms | **OWNER'S RULING APPLIED.** 607 + 33 rows released to PUBLISH; 4 DUNS rows held `INTERNAL_ONLY_PROPRIETARY` on D&B's licence, not on any judgement about the firms |
>
> **The biggest single correction: `Arctic Slope Technical Services, Inc.` is
> NOT one firm.** Two ANC families hold the name, and the declared parents
> separate them — `SGK5EGB9VQM8` and `JRCDHBZD87J1` declare **ASRC**;
> `EB42FC6C9N64` (trading as SIVUNIQ), `WWJXZJT6VKK9` and `JW45GQBY26N3` declare
> **NANA**. The $12.0B directory row takes the two ASRC UEIs only. A naive
> one-name-one-UEI merge was the most expensive wrong attribution available in
> the crosswalk.
>
> **A new general rule, proposed as ENTITY_MATCH_RULES rule 16: a state-equality
> gate is the wrong shape for a nation whose territory crosses state lines.**
> `KFowler Construction` was refused on `directory=AZ, federal=NM`. The Navajo
> Nation is a tri-state nation — AZ, NM and UT — so that disagreement is
> agreement at the level that matters.
>
> ### What is still genuinely yours
> 1. **16.11**, the vendor-list consent question. No agent should touch it.
> 2. **The Native Village of Eyak is not in the spine and $583M turns on it.**
>    Kluti Kaah already carries a tier-X ruling naming Eyak as the true owner
>    and Cedar has nowhere to put the answer. Mint it, or accept the money stays
>    unattributable.
> 3. **NEST-1's ledger rows and the tier-A `Ho-Chunk Nation` CAGE `3VFL3`.**
>    Your ruling already answers it; the ledger is the integrator's file.
> 4. **Two CAGE lookups** — `Kaiva Services` and `Eastern Shawnee Professional
>    Services` (whose own name contradicts the directory's certifier).
> 5. **Item A's 59**, if you want them keyed at all. Cedar loses nothing by
>    leaving them as a stated floor; it loses correctness by guessing them.
<!-- END DQC-CLEARANCE-2026-09-02 -->


## 1. BBAHC repoint — evidence complete, sign-off only

**Decision:** repoint the 742 rows unlinked from `ANRC-BRBYCO-00` (Bristol Bay
Native Corporation) to `SGVF-BRSTLB-00` (Bristol Bay Area Health Corporation),
including UEI `NL5HNWNUFMK4`.

**Evidence, all verified:** BBAHC is a tax-exempt Alaska nonprofit, Dillingham
AK, incorporated 1973, website bbahc.org (SAM system of record); across 191
public USAspending transactions it declares **itself** as its own parent — not
BBNC. Your original FA-01 ruling already said they are different entities; the
unlink half is done and propagated to all 10 tables.

**If YES:** rows re-key to the health consortium; dollars move off BBNC.
**If NO:** rows stay unattributed (current state, honest but empty).
File: `review/rulings_inbox_2026-08-29_agent.csv`.

## 2. Blocklisted parents in as-of ownership queries

**Decision:** may a blocklisted parent (e.g. "GOVERNMENT OF THE UNITED
STATES" roll-ups — 78 of 2,684 edges) ever WIN an as-of ownership query, or
must those edges be excluded from resolution entirely?

**Context:** workstream B's temporal layer resolves owners as of the
transaction date. The 78 edges are real declarations but are registrant
roll-ups, not ownership. Current behaviour: they participate.
**Recommendation:** exclude from winning, keep as evidence rows.

## 3. The $2.1B disagreement bucket — how loud should it be?

9,402 transactions ($2.1B) have an as-of owner that **contradicts** the
shipped `cedar_uid`. These are the highest-value review targets in the
temporal work.
**Decision:** (a) queue them all for review, (b) queue only those above a
dollar threshold (say $10M per UEI-year), or (c) hold until more ownership
dates are harvested?
**Recommendation:** (b) — the top slice will concentrate most of the dollars.

## 4. Grain rulings — workstream E's batch is in (9 items, evidence attached)

Full evidence: `docs/GRAIN_AUDIT.md` + `docs/schema/grain_evidence.json`.
Ranked by dollar consequence:

1. ~~**`prime_contracts_entity_year.csv` — ANSWER FIRST.**~~ **ANSWERED AND
   BUILT — no decision needed. Struck 2026-09-01 (workstream H).** The grain
   is entity-year, `428_rebuild_prime_entity_year.py` collapsed the variants,
   and the table is **6,715 rows with 0 literal duplicates** as of
   2026-09-01 (8,464 − 1,751 surplus name/tier variants + 2 new entity-years,
   exact, and the script refuses to write if that arithmetic does not close).

   **The scary half of the original item was also wrong and must not be
   re-inherited:** "anyone summing `obligations_usd` by tribe-year
   double-counts today" was false. Keyed either way the file summed to the
   identical cent; the real harm was **join fan-out** — a buyer merging *their
   own* table on the promised key got up to 3 copies of *their* rows. Fan-out
   is now 1.000×. Acting on the wrong model would have produced a destructive
   de-dupe. See `NEXT_SESSION.md` §3.
2. `fpds_uei_cage_map.csv` — `uei` repeats 11,455×; even
   (uei, cage, source_file) collides 4,680×. One row per UEI, or per
   observation-in-a-source?
3. `foia_request_index.csv` — `foia_request_id` repeats 381×; no key at
   arity ≤ 6. Defective id, or (request × matched entity) grain?
4. `gaming_projections.csv` — the build log's stated grain is contradicted
   by the data (8 collisions of 116). Which column separates them?
5. `ferc_ex_parte_communications.csv` — its own id collides 56×.
6. `contractor_ranking.csv` — only unique with a MEASURE in the key.
7. `tribal_bond_issuances.csv` — `cusip` blank on all 29 rows.
8. `visitor_record_foia_requests.csv` — only free text is unique.
9. Five 0/1-row tables — uniqueness vacuous; declare grain from intent.

## 4b. ~~Fifteen~~ **Thirteen** tables with literal duplicate rows — pipeline defects, not rulings

**CORRECTED 2026-09-01 (workstream H), by re-measuring all thirteen candidate
files rather than re-reading the earlier count.** `prime_contracts.csv` was the
headline entry here and it is **fixed**: 1,217,768 rows, **0 literal duplicate
rows**, because `430_restore_prime_transaction_key.py` restored the
`contract_transaction_unique_key` the mapper had been dropping — the 80,778
were distinct FPDS transactions all along and *not one row was deleted*.
`prime_contracts_entity_year.csv` is likewise clean at 6,715 rows / 0
duplicates. Where this section and `docs/GRAIN_AUDIT.md` disagreed,
**GRAIN_AUDIT was right**; this section was written before the repair landed.

For awareness, not decision (fixes route to the pipelines). Every figure below
was re-measured on 2026-09-01 and matches `docs/schema/grain_evidence.json`
exactly:

| table | rows | literal duplicates |
|---|---:|---:|
| `faads_transactions_all_agencies.csv` | 2,769,748 | 179,259 (6.5%) |
| `subawards.csv` | 72,837 | 10,770 (14.8%) |
| **`cedar_ruling_ledger_consolidated.csv`** | 15,587 | **6,302 (40.4%)** |
| `cedar_identifier_graph_edges.csv` | 46,051 | 2,451 (5.3%) |
| `cross_dataset_ruling_map.csv` | 7,507 | 2,228 (29.7%) |
| `faads_transactions.csv` | 60,661 | 1,001 (1.7%) |
| `ferc_docket_filings.csv` | 102,615 | 822 (0.8%) |
| `native_passthrough.csv` | 1,262 | 114 (9.0%) |
| `np_schedule_i_grants.csv` | 58,685 | 101 (0.2%) |
| `native_bills_subject_sweep.csv` | 2,414 | 5 (0.2%) |
| `lobbying_registrant_native_ownership_evidence.csv` | 27 | 4 (14.8%) |
| `tcu_cdfi_ownership_evidence.csv` | 130 | 4 (3.1%) |
| `hearing_bill_links.csv` | 465 | 1 (0.2%) |

That is **13 tables** by `docs/GRAIN_AUDIT.md`'s count, which includes
`hearing_bill_links.csv`'s single row. Full evidence per table in
`docs/GRAIN_AUDIT.md`; the running defect ledger is `docs/KNOWN_ISSUES.md`.

## 5. Suspect EIN links — 334 rows, from the first second-source harvest

`review/irs_ein_link_queue_2026-08-29.csv`. Six are self-filing entities
whose EIN files as a DIFFERENT organisation (IAIA → IAIA Foundation;
Chugachmiut (AK) → Lakota Language Consortium (IN)); 328 file cross-state;
7 ledger rows store the entity's name where the filer's belongs. These are
link-quality findings — batch-rule or sample-and-rule as you prefer.

## 6. ~~Grain rulings — incoming from workstream E~~ — SWEEP LANDED, nothing incoming

**Closed 2026-09-01 (workstream H).** The sweep this item was waiting on has
run. It tested candidate keys for all 207 undeclared shippable tables against
the FULL file and landed **185 DECLARED_VALIDATED, 12 OPEN_WITH_EVIDENCE, 13
DEFECTIVE, 0 unexplained**. `contract_grain_unstated_shippable` is therefore
**25, not 207**, and the gate's ratchet floor in
`data/clean/_regression_baseline.json` reads 25.

The 12 that need a human are §4 above; the 13 that need a pipeline fix are
§4b. Nothing further is pending from that workstream.
(`federal_funding_transactions.csv` resolved on its own evidence:
`assistance_transaction_unique_key` is unique on all 701,955 rows across the
seam, so the union of the two pulls was not the problem it was expected to be.)

## 7. Standing items from earlier sessions (unchanged)

**Cross-reference added 2026-09-01 (workstream H): the first three items are
the same three tables `62` reports as `tables_undocumented_in_codebook = 3`.**
That metric and this list have been tracking one set of decisions in two places
with nothing connecting them, so the gate line read as an anonymous backlog and
this list read as optional. They are neither: **these three rulings are the only
thing standing between that metric and zero**, and no agent can close them —
each is a publication decision, not a measurement.

- `gaming_property_locations` publishable filter — 2,212 rows, **1,471
  `publishable = Y` / 741 `N`** (re-measured 2026-09-01)
- `consultation_agency_coverage` split decision — 66 rows
- `wa_machine_transfers` empty-or-real decision — **0 rows on disk**, 18 columns
- B&B git-history decision on the PUBLIC repo (accept vs filter-repo)

---

## 8. Correctness pass 2026-08-29 — three items an agent could not close

*Appended by the correctness agent. §4b's "fifteen tables with literal
duplicate rows" is partly ANSWERED below and the answer changes what it is
asking for.*

### 8a. ~~`ship_dist_rows` cannot return to its floor~~ — RESOLVED 2026-09-01, no ruling needed

**Struck by workstream H after re-running the gate: `py -3 code/62_no_regression_check.py`
exits 0 and prints `no regressions`.** Recommendation (b) was taken and then (a):
the allowance was made per-table and consumable, two further defects in it were
found and fixed while doing so (it compared dist-to-dist when the metric sums
`min(dist, clean)`, and `ship_ratio_pct` then failed on the very fall the line
above had just allowed), the correction-register row was written through
`354_correction_register.record()`, and the baseline was recorded **while
green** at `ship_dist_rows = 8,461,252`. No decision is outstanding here. The
reasoning is kept below because it is the clearest statement in the repo of why
a single-use allowance is the wrong shape.

Collapsing `prime_contracts_entity_year.csv` to its true grain removed 1,749
surplus rows (8,464 -> 6,715). The arithmetic closes EXACTLY —
`8,464 − 1,751 surplus name/tier variants + 2 new entity-years − 0 lost =
6,715`, printed on every run of
`py -3 code/428_rebuild_prime_entity_year.py`, which refuses to write if it
does not close or if any entity-year is lost. No entity-year, and no dollar,
left the file.

`62.ship_dist_rows` is MUST_NOT_FALL and it fell 8,463,001 -> 8,461,252, which
is exactly the 1,749. The gate's sanctioned escape is the correction register's
`rows_removed` declaration — but it compares `b - n` against the **sum of every
declared removal ever**, and the register already carries 55 rows from an
earlier episode that the baseline has since absorbed. So the sum is 1,804 while
the fall is 1,749 and can never match. **The mechanism works once.** That is a
gate defect, not a data defect, and it is not an agent's to fix (`62` is
owned).

**Decision:** (a) re-record the gate baseline now that the collapse is verified
and reconciled — the shelf catches up on the next `build.py ship`; or (b) change
the allowance to be per-table and consumable, matching the per-file allowance
that already exists twenty lines further down in the same file.
**Recommendation:** (b), then (a). The per-file form is already written and
already correct.

### 8b. The FAADS duplication is diagnosed but its repair needs a full rebuild

`faads_transactions_all_agencies.csv` — 179,259 literal duplicate rows — is
**not** a page fetched twice. 174,348 of them (97%) come from one staged
object, `ed_fy2007_archive.zip`; 174,957 are FY2007; all carry an
`award_id_fain`; and the staged zip carries
`assistance_transaction_unique_key` and `modification_number` among its 112
columns, neither of which `30_funding_pre2008.to_out_row` was taking. It is the
same projection loss proved exactly for prime contracting, where restoring the
key took 80,778 "duplicates" to **zero without deleting a row or a dollar**
(`code/430_restore_prime_transaction_key.py`).

`to_out_row` and `OUT_COLS` now carry both columns. Repairing the file on disk
needs `py -3 code/30_funding_pre2008.py build`, a full re-extract of a 2.77M-row
shipped table from staged zips, followed by re-running `503_identity.py stamp`.

**Decision:** run that rebuild, or leave the table diagnosed-not-repaired.
**Recommendation:** run it — the staged zips are all on disk, the fix is proved
on the sibling table, and until it runs the readiness scoreboard is blocking
`funding` on a defect that no longer exists in the code.

> #### CORRECTION APPENDED 2026-09-02 — 8b IS SETTLED, AND ITS RECOMMENDATION IS NOW WRONG
>
> **Do not run `30_funding_pre2008.py build`.** The recommendation above rests
> on two premises and both have since become false. Measured by
> `code/1083_faads_zip_column_census.py` — every CSV member of every staged
> object, header bytes only, **zero unmeasured** — and cross-checked against
> the live table's own `source_file`, **77 of 77 objects with no exception in
> either direction**:
>
> | | source objects | rows | keyed in the clean table | columns on disk |
> |---|---:|---:|---|---:|
> | wide | **17** | 825,754 | **100.0% each** | 112 |
> | narrow | **60** | 1,943,994 | **0.0% each** | 20 |
>
> 1. **The duplication is already repaired, and not by a rebuild.**
>    `code/791_faads_transaction_key_and_repoint.py` (2026-09-01) merged the key
>    on **by content** and took 179,259 literal duplicates to **3,441**, with
>    29,594 of 29,594 attributions re-found and 0 moved. The paragraph above
>    predates that pass.
> 2. **A re-extract would recover ZERO new keys.** The 17 objects that carry
>    the key are already 100% keyed. The 60 that are not keyed are 20-column
>    objects whose bytes never held the column, so there is nothing in them for
>    a re-extract to take. Derivation is closed too: the key is
>    `{sub_agency_code}_{fain}_{uri}_{cfda}_{modification_number}` and the
>    narrow objects carry neither `awarding_sub_agency_code` nor
>    `modification_number`.
> 3. **It would cost the audit trail.** A rebuild re-points `faads_row_id`,
>    which is a ROW POSITION and the anchor for all 29,594 attributions — the
>    exact hazard `791` was built to defend against.
>
> **Recommendation, replacing the one above: leave the table as it stands and
> close the item.** The residual 3,441 byte-identical rows are declared, in
> band, inside the unkeyed FY2001–2006 region, and `cedar_export_safety.csv`
> already books the table `ROW_LEVEL_ONLY / grain UNSTATED`.
>
> **What was done instead**, at zero risk to the row anchor:
> `code/1086_faads_award_key_promote.py` promoted
> **`assistance_award_unique_key` onto 2,769,748 of 2,769,748 rows (100.0%)** —
> read from the 112-column objects' own column, and derived for the other
> 1,943,994 from `usaspending_permalink`, which those 20 columns DO carry on
> 100% of rows. 1,493,774 join groups, **0 ambiguous**, rows and money
> conserved to the cent, `verify` exit 0. It is award grain and makes no grain
> claim; what it buys is that a pre-2008 award can be followed into
> `federal_funding_transactions.csv`.
>
> Full write-up: **`docs/FAADS_TRANSACTION_KEY_SETTLEMENT_2026-09-02.md`**.
> Per-member evidence: `docs/FAADS_ZIP_COLUMN_CENSUS.json`.

### 8c. As-of ownership: 81.4% of prime dollars, and what the shelf should do

`code/429_apply_asof_ownership_status.py` now carries the temporal verdict onto
`prime_contracts.csv` and up into the entity-year panel. Measured over
$244.766B of attributed prime obligations:

| status | rows | obligations | may ship a definite owner |
|---|---:|---:|---|
| CONFIRMED_AS_OF | 151,851 | $45.629B | **yes** |
| RESOLVED_OWNER_NOT_IN_CEDAR | 310,421 | $86.086B | no |
| NOT_EVALUATED | 306,626 | $78.830B | no |
| UNKNOWN_OUTSIDE_EVIDENCE | 58,847 | $18.603B | no |
| AMBIGUOUS_OVERLAP | 41,716 | $10.215B | no |
| NO_FACT_ON_SUBJECT | 9,459 | $2.931B | no |
| **CONTRADICTED_AS_OF** | **9,259** | **$2.074B** | **no — §3 above** |
| NO_COVERING_FACT | 608 | $0.333B | no |
| AMBIGUOUS_GRANULARITY | 75 | $0.066B | no |

`tribe_id` / `cedar_uid` are unchanged: they are Cedar's CURRENT attribution and
remain correctly labelled as that. The new
`owner_as_of_transaction_cedar_uid` names an owner ONLY on CONFIRMED_AS_OF and
reads `UNKNOWN` everywhere else — never filled from current ownership.

**Two decisions this raises.**

1. `517_export_safety.py` treats `asof_status == RESOLVED` as definite. It is
   not: of 10,983 RESOLVED cells only 3,669 carry `agrees_with_shipped = 1`;
   410 carry `0` (the layer CONTRADICTS the shipped owner) and 6,899 are blank
   (a parent resolved that Cedar holds no entity for). **517 currently counts
   all 10,983 as safe**, which is how $86.1B came to be reported as confirmed.
   517 is owned and was not edited. **Decision: adopt the three-way split in
   517's own counts.**
2. `contractor_ranking.csv` — the most owner-centric customer-facing table,
   1,429 rows, `owner_entity_id` + `owner_obligations_usd` — still carries no
   status. It is rebuilt wholesale by `269_build_contractor_ranking.py`, a
   PHASE 1 rebuild with unattributed enricher backups already sitting beside
   it, so it was not rebuilt at the end of a session. `269` reads
   `prime_contracts.csv`, which now carries the status per row, so the roll-up
   is a small change to that script. **Decision: schedule the 269 rebuild.**

---

## 9. The spiderweb harvest — three batches, ranked, evidence attached

*Appended 2026-09-01 by workstream J (`code/523_spiderweb_harvest.py`). Every
row below is **tier B**: a FAR 4.18 / 52.204-17 declaration is evidence of a
declared connection, never proof of Native ownership. Nothing here mints a
spine entity.*

**What changed underneath first.** `13_build_fpds_hierarchy.py` was reading 6
of the 40 files on disk that carry a parent-UEI column. Reading the other 34 —
the FY2007-FY2026 USAspending contract archive, the 2023-2026 assistance
pulls, the assistance subawards, the gapfill universe — took 1.2 minutes and
no network calls, and moved the declared-edge list from **2,901 to 5,167**.
The three batches below are drawn from the larger file.

### 9a. 78 firms declared into a known entity's family — RULE THESE FIRST

**Decision:** for each firm, does it belong in the named entity's corporate
family (a tier-B ownership relationship in the ledger), yes or no?

**Evidence per row:** the literal declared edge, its observation count and
year span, the source extract, the firm's dollars and dataset presence.
File: `review/523_spiderweb_ownership_candidates.csv`, `unambiguous = Y`,
sorted by `priority_rank` — 163 rows over 78 firms and 56 entities,
$0.62B of observed obligations. The top of the queue:

| rank | entity | firm declared into it | obligations |
|---:|---|---|---:|
| 1 | Rocky Boy's Chippewa Cree | STONE CHILD COLLEGE CORPORATION | $88.1M |
| 2 | Hawaiian Native Corporation | GSI PACIFIC INC. | $158.2M |
| 3 | Southern Plains ITO | CENTRAL OKLAHOMA AMERICAN INDIAN HEALTH | $83.2M |
| 4 | Tlingit & Haida | KIRA TRAINING SERVICES LLC | $128.8M |
| 5 | Tlingit & Haida | KIRA AVIATION SERVICES LLC | $40.4M |
| 6 | Kalispel | KAUFFMAN & ASSOCIATES, INC. | $97.3M |
| 7 | Koi Nation | NTVI ENTERPRISES, LLC | $44.8M |
| 8 | Northern Cheyenne | CHIEF DULL KNIFE COLLEGE, INC | $17.4M |

**If YES:** the firm's UEI enters `cedar_identifier_ledger_final.csv` at tier B
with the declaration as evidence; its obligations become attributable.
**If NO:** the row is a tier-X refutation and the declaration stops being
re-proposed every pass.

*`unambiguous` deliberately EXCLUDES single-observation declarations. One
filing is not a pattern: OKLAHOMA STATE UNIVERSITY MEDICAL AUTHORITY declares
CHOCTAW NATION OF OKLAHOMA as its parent on exactly one 2026 row, and it is
not a Choctaw subsidiary.*

### 9b. 246 UEIs that are entities we ALREADY hold — a ledger backfill, not new firms

**Decision:** approve the batch, or require row-by-row sign-off?

This is the biggest single finding of the pass. 258 declared edges are not
ownership at all — they are **one registrant filing under two UEIs**, or a
Cedar entity's own top-level UEI missing from the ledger. `13` drops a
self-edge only when the two UEI strings match, so a renewed or reassigned UEI
survives as a "parent" and reads as a holding company.

    COOK INLET REGION INC        S2SVA1GNRVK5  ->  ANRC-CKINLT-00   $133.2M
    NANA REGIONAL CORPORATION    RA4LQVFLCQC6  ->  ANRC-NANARC-00    $32.8M
    KONIAG, INC.                 DRDKNY4L1T33  ->  ANRC-KONIAG-00    $12.4M
    GOLDBELT, INCORPORATED       P9QQX7RT8E98  ->  ANVC-GLDBLT-00    $11.5M

File: `review/523_identifier_backfill_candidates.csv`. **251 undisputed, 7
disputed** (the declared name resolves to a DIFFERENT spine entity than the
edge's keyed end — those need a ruling, not a batch approval). Two evidence
kinds are kept apart on purpose: `identical_declared_name_on_the_same_edge` is
within-row string equality and carries no spine lookup, while
`matches_the_keyed_entitys_own_spine_name` is a name match against the spine
and is exactly how BRISTOL BAY AREA HEALTH CORPORATION was keyed to the ANCSA
regional. **Review the second kind; the first is safe to batch.**

**If YES:** ~246 UEIs key to entities Cedar already holds — the cheapest
coverage rise available.
**If NO:** they keep arriving as "new holding companies" every pass.

### 9c. 73 existing ledger links this harvest REFUSED to build on

**Decision:** these are not new claims — they are links already IN the ledger
that the harvest declined to inherit from. Rule them, or leave them standing?

`AKNF-INPTBW-00-ARCSLO` (Barrow) holds **103 UEIs, 58 of them `cluster_v3`
"Algorithmic name clustering, unreviewed"**, and the cluster matched on the
word **GOVERNMENT**:

    Ho'olaulima GOVERNMENT Solutions     A+ GOVERNMENT Solutions
    ATI GOVERNMENT Solutions             GOVERNMENT & Industrial Supply
    Qayaq GOVERNMENT Solutions           GOVERNMENT Technical Services
    Koman Propper GOVERNMENT Apparel     Computer Sciences Corporation

Barrow's real subsidiary is UIC **Government** Services LLC. Two more of the
same shape: `KLAMATH 9-1-1 EMERGENCY COMMUNICATIONS DISTRICT` keyed to the
Klamath Tribes and `COUNTY OF MOULTRIE` (Illinois) keyed to Forest County
Potawatomi — the Tuscarawas precedent, a place named for a tribe is not the
tribe.

File: `review/523_suspect_keyed_anchors.csv` — 73 links over 43 entities, each
with its ledger method, its rationale, and the token sets that do and do not
overlap. **The harvest hangs nothing from any of them.**

**If these are wrong:** they are already carrying dollars in shipped tables.

---

## 12. Nonprofits — the 990 mission text says WHY each row is here (shard J, 2026-09-01)

Your question: *"does it say it's native focused in the description... do we have
nonprofits that we know have a reason to be on the master list?"* Yes, and the
corpus was already on disk. `code/541_shard_j_mine_990_mission_text.py` reads
**10,651 local IRS 990 XML returns** (471 MB, no download) and pulls each
filer's `MissionDesc`, `ActivityOrMissionDesc`, `PrimaryExemptPurposeTxt` and
every program-service `Desc`. **4,296 of the 12,764 np_orgs EINs** have a local
return; of the 4,122 whose BMF tier is `full_990`/`990_EZ`, **4,105 (99.6%)** are
already here, and only 12 are absent from the IRS index entirely.

**The answer, as a histogram of `inclusion_basis` (ADR-013), over 4,296 EINs:**

| basis | EINs | what it means |
|---|---:|---|
| `placename_only` | **2,653** | the mission has NO Native word at all, and the row is here because a name token matched |
| `no_native_signal` | 948 | no Native word and no place-name explanation either |
| `subject_classification` | 419 | Native-focused, names no entity |
| `native_serving_not_native_controlled` | 15 | Native people named alongside an explicit broad, non-Native constituency |
| `named_entity` | **132** | the mission names a specific nation or Cedar entity |
| `program_authority` | 49 | ISDEAA / IHS / NAHASDA / ICWA / BIE named in the filing |
| `geographic` | 44 | reservation, trust land, ANCSA region — no nation named |
| `no_mission_text` | 36 | filed (mostly 990-PF) with no mission narrative |

**62% of the nonprofit rows that have a 990 carry no Native word anywhere in
their own mission statement.** That is the size of the place-name defect,
measured for the first time from the organisations' own filings rather than
from their names.

### 12a. The 412 tier-A rows — DECISION: bulk-rule the 21 that state a non-Native purpose

The doc says 412; the file says **697** `confidence_tier = A` rows are
`classification_ruling = UNRULED` (`docs/datasets/06_nonprofit.md` line 26 is
stale). **293 of the 697 have a local 990.** They split:

| basis | n | settleable now |
|---|---:|---|
| `placename_only` | 214 | **21 at `high`** — the filing names a plainly non-Native purpose |
| `subject_classification` | 24 | 9 at `high` |
| `named_entity` | 22 | 9 at `high` |
| `no_mission_text` | 22 | — |
| `geographic` | 7 | — |
| `program_authority` | 4 | 1 at `high` |

The 21 `placename_only / high` rows are the cheapest rulings available. Each
one's own 990 states what it is:

    MOHEGAN FIRE COMPANY INC              "TO PROVIDE VOLUNTEER FIRE AND AMBULANCE SERVICE TO THE COMMUNITY"
    MOHEGAN VOLUNTEER FIRE ASSOCIATION    "...SERVICES TO THE LAKE MOHEGAN, NEW YORK DISTRICT"
    LAKOTA AMBULANCE SERVICE INC          "AFFORDABLE RURAL AMBULANCE SERVICE TO NELSON [COUNTY]"
    APACHE AMBULANCE SERVICE INC          "ambulance service to Town of Apache and surrounding area"
    PEQUOT LIBRARY ASSOCIATION            "...A COLLECTION OF RARE BOOKS, MANUSCRIPTS, AND ARCHIVES"
    JEMEZ VALLEY CREDIT UNION             "...MEMBERS AT LEGITIMATE RATES OF INTEREST"
    PAWNEE CITY PUBLIC LIBRARY FOUNDATION "A STRONG PUBLIC LIBRARY IS THE FOUNDATION..."
    LENAPE VALLEY YOUTH BASEBALL AND SOFTBALL, MOJAVE RIVER ACADEMY SCHOOLS,
    COMMUNITIES IN SCHOOLS PUYALLUP, THE CHEHALIS FOUNDATION, SHOSHONE PROJECT INC,
    SHOSHONE MEDICAL CENTER FOUNDATION, BANNOCK YOUTH FOUNDATION, COQUILLE STUDENT
    LOAN FUND, FRIENDS OF PAWNEE BILL RANCH, CHRISTMAS IN ACTION WICHITA TX,
    CENTRAL DAKOTA ENTERPRISES, DON SHERWOOD ENDOWMENT (ROTARY),
    MOHEGAN VOLUNTEER EXEMPT FIREMENS BENEVOLENT ASSOCIATION

**If YES:** 21 tier-A rows are ruled `place_name_coincidence` on the strength of
the filer's own words, and the tier-A revenue aggregate stops being unquotable
for those rows.

**One to pull out before you sign:** `ROSEBUD ECONOMIC DEVELOPMENT CORP` lands in
this band on the phrase "Rosebud Chamber of Commerce". Rosebud, Texas has one
too, and the text does not settle which Rosebud this is.

The remaining 184 tier-A `placename_only` rows are `medium` (no Native word, but
no affirmative civic purpose either) and 9 are `low` (the filing says "our
culture / our people", so the org may BE the nation talking about itself —
**deliberately not settled**).

Full evidence with quotes: `data/staging/np_mission/inclusion_basis.jsonl`.

### 12b. The mint proposal — 644 candidates, and only 90 are actually mints

`data/staging/np_mission/mint_proposal.csv`, ranked strongest basis first. Every
row carries the verbatim quote and the source XML path.

| proposed action | n |
|---|---:|
| **KEY BY BASIS, do not mint** (no entity is named; the basis IS the claim) | 512 |
| **MINT** as a new nonprofit entity, keyed to the nation it names | 90 |
| **ATTACH EIN to an entity already in the register** — do not mint a duplicate | **42** |

The 42 are the immediate win: organisations already in the 1,555-entity register
whose EIN is simply not attached — Oglala Lakota College, National Indian Health
Board, Native American Rights Fund, Lac Courte Oreilles Ojibwe University and
School, Council for Native Hawaiian Advancement, Fresno American Indian Health
Project, Indian Health Board of Minneapolis, United Tribes Technical College,
California Rural Indian Health Board, Northwest Portland Area Indian Health
Board, Great Plains Tribal Leaders Health Board, and 31 more.

**Recommendation on the architectural question:** do **not** mint ~11,300
nonprofits into a 1,555-entity register. Mint the 90, attach the 42, key the
other 512 by `inclusion_basis` alone, and leave the ~11,300 out. Reasoning is in
the shard report; the short version is that the register has no entity class
that fits a nonprofit, and 11,300 rows of `subject_classification` would swamp
the 1,555 governmental and institutional entities 8:1 while adding no identity
that ADR-013's basis key does not already carry.

### 12c. DECISION: `entity_aliases.csv` holds 104 alias rows that are single English words

Measured while building the matcher. **Every one of the 104 `alias_type='brand'`
rows is a single token**, and among them:

    advantage  applied  ancillary  corporate  cultural  door  feet  field
    fire  indigenous  link  managed  media  nexus  peak  program  research

`cultural` resolves to Southern Ute (`TRBF-STHUTE-00`). `indigenous` resolves to
Delaware Nation (`TRBF-DELAWN-00`). This is the Enterprise Rancheria defect
(`docs/NATIVE_ENTITY_NUANCES.md`) living in the brand registry, and any matcher
reading the alias layer without knowing it will key half a corpus. 541 refuses
all 104 and names each one; nothing else in the repo does.

Two more measured while matching, both worth a rule rather than a patch:

* **"Solo" must be counted on DISTINCTIVE tokens, never on total tokens.**
  *Fond du Lac* is three tokens but only one distinctive one — it keyed the Fond
  du Lac Yacht Club, Rotary Club Charities, County Farm Bureau Cooperative, High
  School Hockey, Volleyball Club, Historical Society, Concert Association and
  nine more Wisconsin civic bodies to the Minnesota Ojibwe band. Tuscarawas,
  wearing a longer name so it clears a token-count guard.
* **The apostrophe must be deleted in normalisation, not spaced.** Spacing it
  turns "St. Mary's" into three tokens, which lets a two-token name pass a
  three-token confidence test: PEORIA SYMPHONY ORCHESTRA keyed to St. Mary's
  (Algaaciq) off the words "ST. MARY'S CATHEDRAL" in a concert-venue list.

**Decision:** withdraw the 104 brand aliases from `entity_aliases.csv`, or retype
them so no matcher can read them as entity names? Shard J did not touch the file.

### 12d. What else the local corpus connects to — measured, not built

| source | volume, local | connects dataset 6 to |
|---|---:|---|
| **Schedule C** lobbying and political activity | **860 returns, 415 EINs (361 of them in np_orgs)**; 222 501(h)-electing and 245 non-electing; $6.14M lobbying by np_orgs filers; **314 narrative blocks / 166 KB of free-text lobbying description**; 124 returns declaring direct contact with legislators, 37 declaring rallies | **dataset 4 (lobbying)** — and it captures advocacy the LDA never sees |
| **Schedule I** grants made | 1,490 returns, 63,628 grant blocks, 60,353 recipient EINs, 89,168 purpose statements | **dataset 3 (funding)** — largely already built: `np_schedule_i_grants.csv` holds 58,685 rows |
| Officers | 141,654 person blocks | governance structure only — **not publishable as a roster** |
| Mission narrative, whole corpus | 10,391 of 10,651 returns carry it | the basis layer above |

Schedule C was the one worth extracting, and it is extracted:
`data/staging/np_mission/schedule_c_lobbying.csv`, 860 rows, grain = one filed
return (a few EIN-years appear twice where the IRS index holds two object_ids
for one period — de-duplicate on `(ein, tax_period_end)` before summing).

**A defect for whoever owns `code/99_build_earmarks_and_schedc.py`:** it already
appends 30 `schedc_*` columns to `np_financials.csv`, but records
`schedc_present = 1` on only **93** rows with a lobbying total of **$82,303**.
Two causes, both measurable here: it reaches a narrower slice of the corpus than
what is on disk, and it reads only the 501(h) `...Grp` shape, so the **245
non-electing filers** who report a flat `TotalLobbyingExpendituresAmt` are read
as zero. That is an undercount, not a coverage limit.

**One limit worth stating plainly:** `native_serving_not_native_controlled` is
assigned to only 15 organisations, and that is a property of the source, not of
the classifier. **A Form 990 does not disclose who controls the filer.** The
tier is assigned only where the filing itself states a broad non-Native
constituency; absence of the tier is never evidence that an organisation IS
Native-controlled. Separating Native-controlled from Native-serving needs a
governance source — bylaws, a tribal charter, a board roster — not the 990.

---

## Do the 30 pre-1907 Osage rows belong in the natural-resources ledger?

*Appended 2026-09-01 by workstream O, after your "1880? What data goes that far
back lol". The question was right. The fields are already fixed; this is the
scope call, and it is genuinely arguable, so it is yours.*

**Decision:** keep the 30 rows for 1880–1906 in `data/clean/resource_revenue.csv`,
or move them out of the natural-resources dataset.

### What is already done, so this is not urgent

The rows were stamped `commodity = "Osage Mineral Estate (oil, gas, sand and
gravel, water use)"` and `land_status = trust`, with confidence **A** on four of
them. The Mineral Estate was created by the **1906 Osage Allotment Act**, and
the first Osage oil lease of any kind was the **Foster lease of 1896-03-16** —
so for 1880–1895 Cedar was asserting oil revenue from an estate that did not
exist. **Corrected**: commodity blank, `resource_type = not_stated`,
`land_status = not_stated`, `revenue_type = trust_disbursement`, all 30 demoted
to **B**, and the sourced explanation carried in `beneficiary_note`. Nothing
deleted — row count unchanged at 11,305.

### What the payments actually were

Louis F. Burns, "Osage", *Encyclopedia of Oklahoma History and Culture*,
Oklahoma Historical Society, entry OS001 — the Osage Trust Estate *"came from
treaty settlements, land sales from the Kansas Reservation, and accumulated
interest on money held in trust by the United States"*; *"Income mainly from
grazing leases caused the commissioner of Indian affairs to call the Osages 'the
richest people on earth'"*; and decisively, *"**Petroleum income did not become
a monetary factor until after Osage allotment in 1906–1907.**"*

Your own prior — trust interest on the Kansas land-sale proceeds — is **the
larger half of the right answer**. The source adds grazing income, which
complicates it: grass-lease income *is* resource revenue. The published figure
is one number covering both and nothing apportions it, so Cedar does not.

### The two answers

**KEEP THEM IN** (current state). They are one continuous series that the Osage
Minerals Council publishes as one table, 1880–2032. Splitting it across two
Cedar tables hides the seam from anyone reading only one of them. The corrected
fields already make the block excludable with a single predicate —
`resource_type = 'not_stated'` or `commodity = ''` — so a subscriber charting
resource revenue drops them automatically.

**MOVE THEM OUT.** The **BTFA precedent points this way and it is squarely on
point.** BTFA was deliberately kept out of this ledger because Interior's own
description makes royalties one of six ingredients: *"Trust funds include
payments from judgment awards, settlements of claims, land-use agreements,
royalties on natural resource use, other proceeds derived directly from trust
resources, and financial investment income."* A pre-1907 Osage payment is that
same mixture. If BTFA is scale context rather than a series, consistency says
these are too.

**If MOVE:** they leave `resource_revenue.csv` and land in a
`data/clean/` sibling for pre-estate distributions, or in `review/` as context.
Cost: the published series gains a 1907 floor and the seam has to be documented
in two places instead of one. About an hour, and it is reversible.

Evidence and both arguments in full:
`docs/datasets/natural_resources_sources.md`, "The pre-1907 classification
correction". Code: `code/83_build_resource_ledger.py`, `_osage_period_fields`.

### 12e. The Fond du Lac token bug, measured against the live resolver — 66 contradictions, and Umatilla Electric is still one of them

Follow-up after the lobbying workstream adopted the brand-alias guard (12c).
The second defect in that list is **not** fixed and it is the more dangerous
one. `data/staging/np_mission/resolver_exposure.csv`, produced by
`py -3 code/541_shard_j_mine_990_mission_text.py --resolver-exposure`, which
calls `503.resolve()` **read-only** and writes only into staging.

**Why a second test was needed.** `503`'s loose path wins on *"the spine
entity's distinctive tokens are a subset of the filed name"*, and its two
guards — `ADMIN_GEOGRAPHY` and `CIVIC_FORM` — are **denylists of words**:
COUNTY, YACHT, ROTARY, GOLF, LIBRARY. A denylist can only refuse a civic form
somebody already thought of. It catches `FOND DU LAC YACHT CLUB`. It does not
catch `ENVISION GREATER FOND DU LAC`, `FOND DU LAC FESTIVALS INC` or
`FOND DU LAC ADULT LITERACY SERVICES INC`, because no word in those names is on
either list. The guards are also blind to the shape itself: *Fond du Lac* is a
two-token distinctive set that is **entirely a Wisconsin city name**, so every
organisation in that city satisfies the subset test.

**The mission text is the orthogonal test, and it runs the other way round.**
Instead of asking whether the filed NAME looks civic, it asks what the
organisation says it does. Crossed over the 830 np_orgs organisations that
`503` keys *and* that have a local 990:

| what the filing says | 503 keys it | 503 does not |
|---|---:|---:|
| `placename_only` | **562** | 2,091 |
| `no_native_signal` | 69 | 879 |
| `named_entity` | 74 | 58 |
| `subject_classification` | 74 | 345 |
| `geographic` | 18 | 26 |
| `program_authority` | 17 | 32 |

The 562 are a screen, not a verdict — a tribal government's own 990 often
says "services to our members" and names no Native word at all, so silence
proves nothing. **The defensible subset is the 66 where the filing states an
affirmative non-Native civic purpose**, over **25 spine entities**:

    UMATILLA ELECTRIC COOPERATIVE ASSOCIATION -> TRBF-UMATLL-00
        "UMATILLA ELECTRIC COOPERATIVE IS A MEMBER-OWNED ELECTRIC UTILITY
         THAT SELLS ENERGY AND OTHER SERVICES..."
    ONEIDA-MADISON ELECTRIC COOPERATIVE INC   -> TRBF-ONDANY-00   electric cooperative
    ONEIDA HEALTHCARE SYSTEMS INC             -> TRBF-ONDANY-00   101-bed acute care hospital
    SENECA HOSE CO NO 1 INC                   -> TRBF-SNCNAT-00   volunteer fire company
    SENECA VOLUNTEER AMBULANCE SQUAD          -> TRBF-SNCNAT-00   ambulance, Seneca IL
    SOUTH ONONDAGA FIRE DEPARTMENT INC        -> TRBF-ONNDGA-00   fire department
    TAOS VOLUNTEER FIRE DEPARTMENT INC        -> TRBF-TAOSPB-00   volunteer fire
    PUYALLUP EDUCATION ASSOCIATION            -> TRBF-PUYLLP-00   teachers' association
    WASHOE EDUCATION ASSOCIATION              -> TRBF-WASHOE-00   Washoe County School District
    WYANDOTTE EDUCATION ASSOCIATION           -> TRBF-WYNDTT-00   Wyandotte public schools
    TUSCARORA TOWNSHIP VOLUNTEER FIRE ASSOC   -> TRBF-TSCARA-00   volunteer fire
    SPORTING WICHITA INC                      -> TRBF-WKWTOK-00   youth soccer club
    ST LUKES HEALTH FOUNDATION OF SIOUX CITY  -> SGVF-NDNHLT-00   regional medical center
    SHEPPTON ONEIDA VOLUNTEER FIRE CO, SENECA ROCKS VFD, SENECA VALLEY
    FOUNDATION, SOUTH SENECA AMBULANCE CORPS, CHEROKEE PASS FIRE DISTRICT,
    SEMINOLE TRAIL VOLUNTEER FIRE DEPARTMENT, ROSEBUD COMMUNITY HOSPITAL, ...

Concentration: Seneca Nation 9, Wichita 6, Cherokee Nation 5, Tuscarora 5,
Mohegan 4, ND Native Health 4, Oneida NY 4, Puyallup 4, Klamath 3, Onondaga 3,
Wyandotte 3, Osage 2.

**`UMATILLA ELECTRIC COOPERATIVE ASSOCIATION` is the $592M leak named at the
top of `docs/datasets/06_nonprofit.md`, and `503.resolve()` still returns
`TRBF-UMATLL-00` for it today** — reason string *"gov-class distinctive-token
match on 'Umatilla Tribe', unique"*. The doc records the symptom; this is the
first measurement of the mechanism still being live in the resolver.

**Decision, three options:**

1. **Feed the 66 to `503` as declared exclusions** (`RESOLUTIONS` entries, the
   TUSCARAWAS pattern). Smallest change, fixes exactly these, fixes nothing
   else — a hand list, which is what the 2026-09-01 guards were written to
   replace.
2. **Add a shape rule to the loose path** — refuse when the spine entity's
   distinctive-token set is entirely a US settlement name and the filed name
   contributes no Native term. This is the general fix and it reaches
   `ENVISION GREATER FOND DU LAC`, which no denylist will.
3. **Let evidence beat the name.** Where Cedar holds the organisation's own
   990 and it states a non-Native purpose, that outranks any name match. This
   is the strongest and it is the only one that scales, because the corpus is
   already on disk for 4,296 of the 12,764.

**Recommendation: 3, with 2 as the fallback where no 990 exists.**
Shard J did not touch `503` — it is another workstream's file and the guard
belongs with its owner, exactly as the brand-alias fix did.

---

## 13. Wire CICD's published figures in as STANDING GATE ASSERTIONS (shard-N, 2026-09-01)

**Decision:** approve (or amend) three checkable assertions so the CICD
benchmark stops being re-derived every session and starts failing a build when
Cedar silently loses data. `docs/CICD_BENCHMARK.md` already computes the
comparison; what does not exist is a **gate** that goes red. A gate that knows
Cedar's FY2000–2021 deflated prime total should sit near $190B catches a
1.2M-row table losing a fiscal year, which no lint class can see.

**Why now.** You measured Cedar against your own CICD benchmark and got
"$164.9B against ~$200B". That comparison is invalid as stated and this session
established why: three of the four axes differ. Deflated to 2021 dollars using
the table's own `deflator_factor_2025`, Cedar's FY2000–2021 attributed prime is
**$189.99B against CICD's $198B prime — −4.05%, inside the CORROBORATED band.**
The nineteen missing fiscal years are worth roughly **$2B nominal**, not $35B.
Full working and per-source coverage table: `docs/datasets/02_contracting.md`
§COVERAGE.

### Proposed assertions

| id | assertion | source, with year | current value | proposed tolerance |
|---|---|---|---|---|
| `CICD-A1` | Cedar's attributed prime obligations for FY2000–FY2021, expressed in **2021 dollars**, are within 10% of **$198B** | CICD, *Federal contracting's expanding revenue role in Indian Country*, 2022-12-21 — *"$202 billion in revenue (in 2021 dollars) … $198 billion from prime contracts and $4 billion from subcontracts"*, 1981–2021 | **$189.99B** (−4.05%) | ±10%. A one-sided floor is wrong here: Cedar going far ABOVE $198B would mean the attribution has started over-claiming, which is the failure this project most needs to catch. |
| `CICD-A2` | `prime_contracts.csv` holds **every fiscal year FY2000–FY2026 inclusive**, none with zero rows, and `min(fiscal_year) == 2000` | Cedar's own documented boundary — the FY2000 floor is now sourced, not accidental | FY2000–FY2026, 1,217,768 rows, no gaps | exact. This is the cheap one and it is the one that would have caught a lost year. |
| `CICD-A3` | DoD share of Cedar's attributed FY2000–2021 obligations is within 10% of **67.6%** | CICD, *Native entities and the federal contracting landscape*, 2023-06-21 | 63.76% (−5.7%) | ±10%. Currently typed UNEXPLAINED at 5%; at 10% it is a gate rather than an open question, and the open question stays in `CICD_BENCHMARK.md` where it belongs. |

**Deliberately NOT proposed as assertions:**

- *"~$200 billion in the last decade"* (2026-08-24). It is prime **plus** sub,
  and Cedar's subaward layer is a known floor — FY2021–24 hold 173/89/120/166
  rows against ~5,000/yr either side. An assertion whose input is broken tests
  the input, not the claim.
- *"$26.6 billion in 2025."* CICD's 2025 is calendar-year and Cedar's is fiscal;
  the quarter of difference falls in a rising series, and USAspending back-fills
  obligations for months after year-end. Two moving parts, no signal.
- Anything counting **contracts**. `SANITY-04` is still UNEXPLAINED: no Cedar
  award key reproduces CICD's 50,167 (parent PIID 15,985 · PIID 173,716 ·
  PIID+UEI 221,058) and CICD does not state its key. Do not gate on a number
  whose grain is unknown on both sides.

**If YES:** the three land in `docs/ASSERTION_LAYER.md` with source and year,
and `62_no_regression_check.py` (or whichever gate you prefer) gains a class
that goes red on a silent data loss. **If NO:** they stay as prose in
`CICD_BENCHMARK.md` and every future session re-derives the comparison, which
is how "$164.9B vs $200B" got stated as a shortfall in the first place.

**Second question, and it is one only you can answer.** `CICD-A1` depends on a
deflator. Cedar uses `deflator_factor_2025` (FY2000 = 1.77359, FY2021 =
1.170557). **CICD's 2022 article does not state which index it used.** You
built that dataset — was it CPI-U, the GDP implicit price deflator, or
something else? If the two indices differ, the −4.05% is partly an artefact of
the comparison itself and `CICD-A1`'s tolerance should widen.

---

## 14. The $65.2B unattributed pool — ranked, characterised, NOT attributed (shard-N, 2026-09-01)

**Not a decision — a worklist**, filed here because the ranking materially
changes what `503`/`510` should do next and because the headline number has
been quoted without its decomposition.

328,906 rows / **$65.24B** sit at tier C with `attributed_flag = 0`. Every row
carries a UEI; 105,688 carry a CAGE. Split by `ruling_status`:

| ruling_status | rows | obligations | distinct UEI | what it means |
|---|---:|---:|---:|---|
| **(never ruled)** | 262,079 | **$52.06B** | 9,160 | nobody has looked |
| `RULED_NOT_NATIVE` | 34,140 | $5.80B | 139 | correctly excluded, will never attribute |
| `RULED_CLASS_ONLY` | 28,940 | $5.46B | 34 | **Native, owner not in the spine** |
| `RULED_HOLD` | 914 | $0.80B | 17 | held |
| `RULED_OWNER_NOT_IN_SPINE` | 1,789 | $0.47B | 6 | owner identified, entity absent |
| `RULED_TIER_UNSTATED` | 936 | $0.38B | 29 | tier missing on the ruling |
| `RULED_TIER_C_NOT_ATTRIBUTED` | 96 | $0.27B | 1 | |
| `RULING_CONFLICT` | 12 | $0.001B | 3 | |

**79.8% of the money has never been ruled on. Only 8.9% has been ruled NOT
Native.** "Unattributed" has been reading as "rejected"; it means "unexamined".

**Where to start, and it is not the top of the dollar list.** The best signal is
a never-ruled row that carries a **Native-preference set-aside**: $16.99B across
65,492 rows. Inside that, **10,877 rows / $720M sit on Buy Indian or Indian
Business set-asides, which are statutorily Native-only** — an unattributed row
on one of those is a near-certain Native entity awaiting a name, and it is the
cheapest yield per ruling in the whole pool.

**It is a long tail.** 11,857 distinct never-ruled awardee names; the top 50 are
only 22.1% of the money. There is no top-20 sweep that closes this.

**Two cautions, both load-bearing.**

1. The pool contains obvious non-Native rows. The single largest never-ruled
   awardee is **`THE BAHRAIN PETROLEUM COMPANY BSC (CLOSED)`, 40 rows /
   $990.8M**, with no Native set-aside on any of them. Do not read $65.2B as
   latent Native dollars.
2. `RULED_CLASS_ONLY` at $5.46B on **34 UEIs** is the concentrated, tractable
   slice — Cedar already knows this money is Native and cannot name the owner.
   34 owner determinations move $5.46B. That is the highest dollars-per-ruling
   in the table and it needs entity work, not a filter.

Ranking, ready to work: `data/staging/pre2000_probe/unattributed_ruling_dollars.json`
(`never_ruled_top_50_awardees`) and `benchmark_reconciliation.json`
(`top_60_awardees_by_obligation`). Produced by `code/564` and `code/565`, both
read-only. **Shard-N attributed nothing and touched no ruling.**

### AMENDMENT to item 13, same session — CICD publishes its series year by year, and it changes the assertions

The 2022 article prints charts, not tables. **The complete year-by-year series
is in the page's `__NEXT_DATA__` payload** — `docs/HIDDEN_DATA_TECHNIQUES.md`
item 2, applied to a research article. `code/567` extracts it, validates it
against the article's own headline (three entity series sum to **$197.987B**
against the stated **$198B**, 0.007% off), and stages it at
`data/staging/cicd_published/cicd_prime_series_1981_2021.csv`.

That makes `CICD-A1` far sharper than a 41-year total, and it produces a
finding worth more than the assertion:

| window | CICD (2021$) | Cedar attributed (2021$) | delta |
|---|---:|---:|---:|
| 1981–1999 | **$0.354B** | $0 (Cedar holds no rows) | −$0.354B |
| FY2000–2007 | $32.508B | $24.858B | **−$7.644B, −23.53%** |
| FY2008–2021 | $165.124B | $165.131B | **+$0.007B, +0.004%** |
| FY2000–2021 | $197.633B | $189.989B | −3.87% |

**Two things follow and both matter more than the gate.**

1. **CICD's own 1981–1999 total is $354M — 0.179% of its own $198B.** 1982–1987
   and 1989 are literally zero in CICD's published data. The "nineteen missing
   years" are not a hole worth chasing; they are a rounding error, and this is
   the incumbent's own number saying so.
2. **The entire −$7.6B is FY2000–FY2007.** From FY2008 the two builds agree to
   four decimal places, which is the strongest external corroboration Cedar
   Press has ever produced about itself.

**Amended `CICD-A1`, proposed:** assert against **CICD's published FY2000–2021
subtotal, $197.633B**, not the 41-year headline, and split it —
`CICD-A1a` FY2008–2021 within **±3%** of $165.124B (currently +0.004%, so a 3%
band is a real gate rather than a decorative one), and `CICD-A1b`
FY2000–2007 within **±30%** of $32.508B (currently −23.53%, and tightened to
±10% once item 15 lands). Splitting matters: on the combined window a fixed
FY2000–2007 and a newly broken FY2008–2021 would cancel and the gate would stay
green.

---

## 15. FY2000–FY2007 is short by 23.5% and the fix is a file already on disk (shard-N, 2026-09-01)

**Decision:** authorise the **date-gated merge of HigherGov `Data Request
4-5-2023 File 2.csv`**, or rule that it stays out and Cedar publishes
FY2000–2007 as a known 23.5% floor.

**The measurement.** Cedar is within ±7% of CICD in every fiscal year from
FY2008 and short by **16–35% in every one of FY2001–FY2007**. FY2000–2007:
Cedar $24.858B against CICD $32.508B, **−$7.644B in 2021 dollars**.

**The cause is a selection-doctrine failure, and `docs/PULL_DISCIPLINE.md`
predicts this exact shape.** FY2000–FY2007 has exactly one source:
`master prime file.dta`, which is HigherGov **File 1 — the flag-at-award leg
alone**. File 1's 78,267 pre-2007 keys match the clean table's 78,267 exactly,
so nothing was lost in ingestion; the leg was simply never joined to its
partner. **File 2, the SAM-registration leg, has never been merged into
anything** and carries **26,240 net-new pre-2007 keys worth $7.93B nominal**
against a measured shortfall of $7.65B in 2021 dollars. Those are not proven to
be the same dollars and nothing here should be written as if they were — but
one leg run alone for eight years, costing about a quarter of the money, is
precisely what the selection doctrine says happens.

**Why it has not been done, and why that is right.** File 2 matches on
*current* registration. Its author flagged the defect unprompted in 2023:
*"it will pick up awards for companies before they were acquired (e.g., it
would pick up all of Vistronix's awards before ASRC Federal bought them)."*
ASRC is also the largest tier-A net-new entity in the file at $1.32B. Merged
naively, File 2 books a firm's pre-acquisition revenue to the tribe that later
bought it — a false attribution that would look impeccably sourced. **File 2 is
not a merge; it is a merge plus an adjudication**, date-gated against
`ownership_events.csv`, with rows preceding an acquisition held at tier B or
excluded and flagged.

**If YES:** FY2000–2007 closes toward CICD and `CICD-A1b` tightens to ±10%.
**If NO:** FY2000–2007 is published as a stated floor, and the −23.5% goes in
the codebook rather than being discovered by a reader with CICD's article open.

Evidence: `data/staging/cicd_published/cedar_vs_cicd_by_year.csv`;
`docs/datasets/02_contracting.md` §COVERAGE; `docs/PRE2007_SPENDING_SOURCES.md`
Part 2. **Shard-N merged nothing and attributed nothing.**

---

# 16. THE `review/` BACKLOG, RANKED — first whole-directory sweep (int-3, 2026-09-01)

*Full triage: `docs/REVIEW_BACKLOG.md`. Machine-readable: `data/staging/review_backlog_triage.csv`.*

**364 CSV files, 138 MB, and no gate has ever counted them.** Swept whole for
the first time today. The counts:

| bucket | files | rows |
|---|---:|---:|
| PROMOTABLE NOW | 3 | 374 |
| **NEEDS AN OWNER RULING** | **104** | **185,340** |
| SUPERSEDED (flag, never delete) | 27 | 13,452 |
| DIAGNOSTIC ONLY | 230 | 182,633 |

**The finding is that `review/` is mostly NOT a backlog.** 63% of it is the
project's evidence layer — refusal logs, coverage audits, series-break
registers, probe outputs. Those are marked so nobody triages them again.

What is left is **eleven questions**, below, in the order that disposes of the
most rows per answer.

> ## STATUS, updated 2026-09-01 after the owner changed the standing rule
>
> The owner, same day: *"I don't care about you listing issues, you decide how
> to fix them. The only thing I should need to adjudicate is uncertain native
> entities — but even then you can review websites and SAM or annual reports as
> long as you document the decisions and learn from them."*
>
> **Nine of the eleven are now DECIDED.** Write-up with the evidence behind each:
> **`docs/REVIEW_BACKLOG_RULINGS.md`**. Per-row dispositions:
> `data/staging/review_backlog_class_dispositions.csv` (15,911 rows) and
> `data/staging/master_queue_identifier_adjudication.csv` (579 rows). Four new
> numbered rules went into `docs/ENTITY_MATCH_RULES.md` as rules 7–12 so the
> next thousand rows are cheap.
>
> | still yours | why it was not decided |
> |---|---|
> | **16.11 vendor-list consent** (62 rows) | Not a method question. It is a decision about Cedar's relationship with the nations whose lists these are, and the one failure mode that would damage this project's standing rather than its accuracy. Recommendation below unchanged. |
> | **16.5 OSHA** (711 establishments / 1,879 filings) | Owned by INT-1, handed over with the evidence. |
>
> **Nothing was applied to a shipping table.** Every decision is a disposition
> with its evidence attached; applying them to the ledger or the spine is a
> separate, reversible pass that must run against a green gate.

Every item is an attribution, a tier promotion or a scoping call, and Cedar's
standing rule remains that only tier A publishes.

---

### 16.1 — THE IDENTIFIER-GRAPH SCOPING DOCTRINE · unblocks **102,051 rows** across eight `523_*` files

**The question, asked once:** *how far down the unkeyed-identifier ranking does
Cedar key, and on what evidence?*

**The evidence.** `523_idgraph_q3_unkeyed_by_dataset_count.csv` ranks **90,539
unkeyed identifier nodes carrying $506.5B observed**, by how many datasets see
them. The distribution is extremely thin at the top: only **346 nodes appear in
2+ datasets and 22 in 3+**, and the **top 100 alone carry $17.4B**. Alongside it
sit 9,814 name clusters (q2), 708 split-entity suspects (q4), 200 co-occurrence
rows (q1), 300 ownership candidates, 258 backfill candidates, 159 candidate
firms and 73 suspect anchors.

**Recommendation — a THREE-LINE doctrine, not 90,539 decisions:**

1. **Key the top 100 by observed dollars, by hand.** $17.4B, one sitting.
2. **Auto-key nothing below `n_datasets >= 2`** (346 nodes). One dataset seeing
   an identifier is one source's spelling, not corroboration.
3. **The rest are a stated coverage floor**, published in the codebook as
   "N identifiers observed and not keyed", never as an implied zero.

**A caution on the two candidate files inside this group.**
`523_spiderweb_ownership_candidates.csv` (300 rows, $2.28B observed) rests on
**SAM-declared parent/child edges** — an identifier relationship the registrant
filed, which is the strong form, and 22 rows are both `rule_first` and
`unambiguous`. `523_identifier_backfill_candidates.csv` (258 rows, $851.7M) does
**not**: 216 of its rows rest on `identical_declared_name_on_the_same_edge` and
42 on `matches_the_keyed_entitys_own_spine_name`. Both are name equality,
narrowed by an edge but still name. **Rule the 300 before the 258, and rule them
by different standards.**

---

### 16.2 — THE ADJUDICATION-HUB PARTY METHOD · unblocks **15,999 rows** across seven files

**The question:** *may a party named in an IBIA/IBLA decision, a FERC docket or
an ex parte filing be linked to a Cedar entity by the resolver's proposal alone,
and if so at what tier?*

**The evidence.** `168_link_adjudication_hubs.py` produced a proposed entity for
every one of these and then correctly refused to write any of them:
`168_admin_appeal_unresolved_parties` 4,642 · `168_ferc_unresolved_parties`
4,058 · `168_ferc_ex_parte_unresolved` 2,419 · `admin_appeal_unresolved_organisations`
4,289 · `admin_appeal_entity_link_candidates` 420 · `168_foia_link_audit` 166 ·
`168_resource_revenue_ceiling` 5. Every one carries an empty `YOUR_RULING`.

**Recommendation:** rule the METHOD, at **tier B**, and only where the party
name matches a spine canonical name *and* the docket state matches the entity
state. A docket party is a legal filing, so the name is the party's own — but it
is still a name, and `UMATILLA ELECTRIC COOPERATIVE` resolved to a tribe by
exactly this route until a guard went into `503_identity.py` today.
**Start with `168_resource_revenue_ceiling` — 5 rows, and it tests the doctrine
for the price of a coffee.**

---

### 16.3 — THE SELF-CERTIFICATION CEILING · unblocks **15,557 rows**

**The question:** *does a SAM `awardeeBusinessTypeName` Native flag ever get a
firm into the Cedar universe on its own, and at what tier?*

**The evidence.** `esm_native_entity_candidates_2026-08-12.csv` holds **12,645**
federal recipients carrying such a flag, with dollars, transaction counts and an
`evidence_grade`; `sam_individual_native_candidates_2026-08-26.csv` holds a
further **2,912**. `docs/INDIVIDUAL_NATIVE_CLASS_PROPOSAL.md` §4 already puts
the ceiling at **tier C**, and tier C never publishes alone.

**Recommendation:** **confirm tier C as a hard ceiling and close both files as
a stated universe floor.** A self-certification is the registrant's claim about
itself, and Cedar's premise is that it does not republish claims as facts. The
promotable thing here is the *aggregate*, and that is now done — see
`data/clean/sam_native_class_distributions.csv`, promoted today, which is
aggregate-only and small-cell suppressed.

---

### 16.4 — DOES A TEXT MENTION MAKE IT THAT ENTITY'S COMMENT? · unblocks **4,806 rows**

**The evidence.** `regulations_gov_comment_candidates.csv`: 4,806 regulations.gov
comments where a Cedar entity is named in the comment TEXT but not in the title.
`data/clean/regulations_gov_comments.csv` currently ships **172 rows, all
`TITLE_NAMES_THE_ENTITY`** — the text-mention class is excluded on purpose.

**Recommendation: NO — keep them out of the comment table**, and instead ship
the count as a `mentions` measure on `regulations_gov_entity_coverage.csv`. A
comment that criticises a tribe mentions it as loudly as one filed by it, and
the table's unit of analysis is *the tribe speaking*.

---

### 16.5 — OSHA GAMBLING ESTABLISHMENTS · unblocks **711 establishments / 1,879 Form 300A filings**, plus 1,852 more

**HANDED TO INT-1, who owns the labor promotion.**

**The evidence.** `employment_osha_unmatched_2026-08-07.csv` — 711 establishments
whose `n_filings` sum to exactly **1,879** — held because each *"shares a
distinctive token with a Cedar property but no exact name+state match"*
(e.g. `Pearl River Resort, Choctaw MS`, 3,233 employees, token `pearl`).
`YOUR_RULING` filled on **zero** of 711. The later, wider
`osha_gambling_unresolved_2026-08-26.csv` holds 4,560 rows of which **2,708
already carry a blocking verdict** and **1,852 are genuinely open**.
`data/clean/gaming_employment_observations.csv` already holds 874 OSHA rows, so
this is an extension of a live table, not a new one.

**Recommendation:** rule the two files TOGETHER — they overlap — and rule the
*rule*, not the rows: **a shared distinctive token is not a match.** Accept only
`name + state + NAICS 7132xx/7211xx` exact, and publish the remainder as a named
coverage gap.

---

### 16.6 — THE MASTER QUEUE, NEVER OPENED · unblocks **6,559 rows, $82.1B at stake**

**The evidence.** `MASTER_QUEUE_2026-08-07.csv` — 6,559 ranked entity questions,
each with `dollars_at_stake`, an evidence URL and a written question.
**`YOUR_RULING` is filled on ZERO of them.**

> **CORRECTION, same day, against my own earlier figure.** An earlier draft of
> this item said the `_already_ruled_removals/` corpus overlaps this file "by
> exactly 1". **That was wrong and it was wrong for the reason this project
> keeps writing down: the join key was blank.** 2,443 of the 6,559 rows carry an
> EMPTY `identifier` column, so joining on it matched almost nothing and
> reported a queue as wholly unseen. The UEI is present — inside the free-text
> `question` — and read from there the real overlap is **223 rows carrying
> $10.8B of the $82.1B, 3.4% already ruled**. Six of the top fifty by dollars
> are already-ruled rows still sitting here with an empty `YOUR_RULING`,
> including `SAN CARLOS APACHE TRIBAL COUNCIL` ($847M), `LUMMI INDIAN BUSINESS
> COUNCIL` ($696M) and `HOOPA VALLEY TRIBE` ($495M), all removed from the live
> queue on 2026-08-26. **The MASTER QUEUE is partly stale and does not say so.**

**Recommendation:** do not attempt it as a queue. **Sort by `dollars_at_stake`
and rule the top 50** — the ranking exists precisely so the tail never has to be
read — then close the rest into 16.1's stated floor.

**DONE, 2026-09-01.** All 50 adjudicated by `code/604_adjudicate_master_queue_by_identifier.py`
— 23 ACCEPT, 18 REFUSE, 6 ALREADY_RULED, 2 HOLD, 1 FLOOR, none left open. See
`docs/REVIEW_BACKLOG_RULINGS.md`.

---

### 16.7 — 1,223 PROPOSED TIER B → TIER A PROMOTIONS

**The evidence.** `entity_key_tierB_promotion_queue_2026-08-06.csv`: dataset,
source name, proposed tribe, row count and basis, per row.

**Recommendation: rule by BASIS, not by row.** Group the 1,223 by the `basis`
column, rule each basis once, and let the ruling fan out. **THE FIVE THINGS
THAT WILL BITE YOU #1 applies here in full:** the exactness of a key says
nothing about the correctness of a link, and 821 tier-B `need_v6` rows are
6.5% accurate.

---

### 16.8 — 1,049 NAGPRA ALIAS PROPOSALS

**The evidence.** `nagpra_alias_proposals.csv`, written today by script 77 —
proposed aliases harvested from NAGPRA notices, with notice counts and an
example document. `YOUR_RULING` empty on all 1,049. Precedent: of the earlier
recognition-alias pass, **76 of 228 proposals were dropped on review** — a 33%
reject rate, so these cannot be auto-applied.

**Recommendation:** rule only aliases seen in **3+ notices** and reject the
long tail. An alias is an identity assertion about a tribe; a one-notice
spelling is a typesetter, not a name.

---

### 16.9 — 6,796 UNRESOLVED CONGRESSIONAL EARMARK RECIPIENTS

`earmark_unresolved_2026-08-07.csv`, with amount requested, amount enacted and a
source URL per row. Recipient names are as printed in the committee table.
**Recommendation:** same doctrine as 16.2 — name + state exact, nothing else,
remainder published as a floor.

---

### 16.10 — 6,094 SUBAWARD PARTIES (2026-08-28 API route)

`subaward_api_unresolved_2026-08-28.csv`, each with a proposed `tribe_id`,
canonical name, `resolver_how` and confidence tier. **Supersedes** the 4,254-row
`subaward_matches_2026-08-07.csv`, which is recommended for `graveyard/`.
**Recommendation:** rule by `resolver_how`, one ruling per resolver.

---

### 16.11 — THE 62-TRIBE VENDOR-LIST REGISTRY: A CONSENT RULING, NOT AN EFFORT ONE

**This one was nearly promoted and should not have been.** It reads like a
finished registry of tribal vendor and ownership-certification lists — verdicts,
URLs, entry counts, formats. Re-measured 2026-09-01:

- **`publishable = N` on all 62 rows**
- **`consent_status = UNRESOLVED` on all 62 rows**
- 8 rows `TERMS_STATED_RESTRICTIVE`, 2 `ROBOTS_DISALLOW`
- every row carries a `suppression_key`
- and it is **live** — `570_shard_l` and `571_shard_m` wrote it today

**The question:** may Cedar publish the *existence and location* of a tribe's
own published vendor list — a fact about a public website — when the site terms
are restrictive or silent and no tribe has consented?

**Recommendation: split it.** Publish the *verdict* (`LIST_FOUND_PDF`,
`NO_LIST_FOUND`, …) and the *URL*, which are facts about a public page; publish
**no harvested list contents** from any of the 8 restrictive or 2
robots-disallowed hosts without written consent. That converts 62 rows from
`publishable = N` to a shippable coverage table without touching a single
harvested record.

---

**Rows these eleven rulings would unblock, in total: ~155,000 of the 185,340
sitting in the NEEDS AN OWNER RULING bucket.** The remaining ~30,000 sit in 93
smaller files, each listed with its own one-line reason in
`docs/REVIEW_BACKLOG.md`.


---

## 10. Nonprofits — shard-I harvest — 2026-09-01

*Appended by workstream SHARD-I. **Nothing below has been applied.** No `tier`, no `classification_ruling`, no spine row and no `np_orgs.csv` cell was written. Every quote is a literal substring of bytes retrieved and kept on disk under `data/staging/np_harvest/raw/`.*

### 10a. FIRST — the `412` in the dataset doc is not a measurement

`docs/datasets/06_nonprofit.md` says *"412 tier-A rows are awaiting a ruling."* That number is a **hardcoded string literal** in `code/24_generate_dataset_docs.py` (~line 506). It is not computed from `np_orgs.csv` and it does not move when the data moves. `docs/FACT_CHECK_2026-08-06.md` B-25 already flagged it as wrong once.

**Measured against the live file today:**

| | rows |
|---|---:|
| `confidence_tier = A` | 712 |
| …of which `classification_ruling = UNRULED` — **the real backlog** | **697** |
| …in shard-I's strata (`990_N` / `not_required_to_file` / `UNKNOWN`) | 480 |
| …in shard-J's strata (`full_990` / `990_EZ`) | 217 |

**Decision:** may the doc generator compute this figure from the data instead of carrying a literal? **Recommendation: yes.** A hardcoded count in a maintenance doc is a fact with no error term — it cannot be wrong loudly, only quietly. The same applies to the `$592M` / `$497M` figures in the same bullet, which the fact-check also found stale.

### 10b. Tier-A ruling evidence — 480 organisations, split four ways

Shard I fetched each organisation's **own website** and recorded what it says it is. `resolves_to` is an evidence-backed candidate label. **It is not a ruling and must not be applied as one.**

| `resolves_to` | orgs | what the evidence is |
|---|---:|---|
| `native_entity` | **4** | the org's own page asserts a Native control or charter relationship |
| `placename_only` | **35** | the org's own page describes a member-owned, county or denominational body with no Native content |
| `native_serving_not_native_controlled` | **19** | Native language, but no control, charter or ownership asserted |
| `undetermined` | **422** | no readable page — see 10c |

File: `data/staging/np_harvest/tier_a_ruling_evidence_shard_i.csv` — one row per organisation, with the quote, the source page and the raw bytes path.

**Strongest `native_entity` evidence** (own words):

| EIN | organisation | the organisation's own sentence |
|---|---|---|
| 311328543 | ZUNI CHRISTIAN MISSION SCHOOL | "By God’s grace, what began in 1897 as pioneer mission work of the Christian Reformed denomination, has matured into a ministry that is governed by local boards of Zuni Christians—an unparalleled accomplishment in mission efforts among the Pueblo tribes of the…" |
| 933214988 | NISENAN MIWOK COLLECTIVE | "Jane Rey at Frank’s Exchange Who We Are The Nisenan Miwok Collective 501(c)(3) is the nonprofit arm of the Southern Hill Nisenan Tribal community." |
| 331174840 | LIPAN APACHE TRIBE OF TEXAS INC | "[] The Lipan Apache Tribe of Texas is a historical Native American tribe, and the 501c(3) Lipan Apache Tribe of Texas, Inc, is an instrumentality of the tribe, not the tribe itself." |
| 910891385 | TLINGIT AND HAIDA INDIANS OF ALASKA-WASHINGTON CHAPTER | "In 1912 the Alaska Native Brotherhood (ANB) was founded by Tlingit, Haida and Tsimshian leaders who united to work to correct the injustices experienced by Alaska Natives throughout the Territory of Alaska." |

**Strongest `placename_only` evidence** — the Umatilla Electric shape, recommended for demotion out of tier A:

| EIN | organisation | revenue on file | what its own site says it is |
|---|---|---:|---|
| 852069418 | APACHE LEAP MEDIA | — | Z89.3 & 101.5 HD3 KZAO |
| 860828870 | PARTNERS FOR PAIUTE NEIGHBORHOOD CENTER | — | Partners for Paiute \| Community assistance |
| 873791650 | CAHUILLA ELEMENTARY PARENT TEACHER ORGANIZATION | — | Charity \| Cahuilla Elementary PTO \| Palm Springs |
| 800302641 | MOJAVE ARCHERS | — | Mojave Archers |
| 330964160 | MOJAVE RIVER VALLEY HORSEMENS ASSOCIATION | — | MRVHA \| Horse Shows & Events in Apple Valley |
| 920435652 | MOJAVE TRAILS OUTREACH & FOOD PANTRY | — | Mojave Trails Outreach & Food Pantry |
| 922962028 | MON PETIT MOJAVE FOUNDATION INC | — | Mon Petit Mojave |
| 272857715 | STRAIGHTWAY M B C OF MOJAVE | — | Straightway MBC of Mojave |
| 222523902 | MOHEGAN & PEQUOT MODEL RAILROAD CLUB INCORPORATED | — | Mohegan Pequot Model Railroad Club Inc. |
| 222720928 | PEQUOT CYCLISTS INC | — | Pequot Cyclists |

**`native_serving_not_native_controlled`** — the distinction the 990s are worst at, and the reason a website pass was worth running. Serving is not control; the doc's own Jemez Mountains Electric note is the precedent.

| EIN | organisation | the sentence that carries Native language |
|---|---|---|
| 453844277 | OGLALA PET PROJECT | "Oglala Pet Project (OPP) is a 100% volunteer driven, community based 501(c)3 non-profit organization located on the Pine Ridge Indian Reservation in South Dakota." |
| 462925916 | ZUNI PUEBLO MAINSTREET | "How are you doing these days?) Zuni Pueblo became the first Native American community to be designated as a MainStreet Community in the United States in July of 2012." |
| 920124517 | ALEUT FOUNDATION | "Looking ahead, Mei hopes to become a physician serving underserved communities, especially Indigenous populations." |
| 884129140 | APACHE KNIFE FOUNDATION | "[] Tci-He-Nde, Western Apache people, Fort Apache Indian Reservation, San Carlos Apaches, the Chiricahua Apache Nation, Ndee, Nde, GoFundMe, fundraising, Charity, New Charity, Apache Coffee, Apache, Robert Redfeather, Redfeather, Chiricahua…" |
| 881907630 | CHEEE FOKAA BAND OF NORTHEASTERN POMO | "Chhé’ee Ti’dóo (Salt Spring Valley) Our Mission History Get Involved ﻿ Contact Us Our Mission — Chhé'ee Fókaa Band of Northeastern Pomo 0 Skip to Content Our Mission Our Language History Get Involved Contact Us Open Menu Close Menu Our Miss…" |
| 364896186 | SANTA YNEZ CHUMASH OCEANOGRAPHIC INSTITUTE | "Facing Uncomfortable History: Native American Boarding Schools An introduction to forced assimilation in Native American boarding schools." |
| 841432104 | FRAY ANGELICO CHAVEZ CHAPTER GSHA- PUEBLO | "About Home Events About Publications FACC Library Videos Contact Links Photo Gallery Menu FACC-GSHA Home Events About Publications FACC Library Videos Contact Links Photo Gallery The Fray Angelico Chavez Chapter (FACC) is a non-profit organ…" |
| 237171302 | MOHEGAN STRIDERS ASSOC | "Chief Harold Tantaquideon, direct descendent of Uncas, Chief of the powerful Mohegan Nation, joined retired sports writer John DeGange in this unique honor." |

**Decision:** apply these as rulings in bulk by `resolves_to`, or read the quotes row by row? **Recommendation: bulk-apply `placename_only` where the page is substantive and carries zero Native language** (that is a strong negative and it is where the tier-A revenue leak lives), and **read `native_entity` row by row** — a promotion is the expensive direction to get wrong.

### 10c. The finding that decides whether the rest is worth attempting

**392 of the 480 tier-A organisations in shard-I's strata are UNREACHABLE BY WEBSITE** — they supplied no website on their e-Postcard and Cedar holds no e-file return for them. There is no page to read, so `undetermined` here means *no instrument existed*, not *the evidence was ambiguous*.

This generalises. Measured on the **whole** `990_N` population rather than a sample, from the IRS e-Postcard bulk corpus (one request, 93 MB, `Last-Modified 2026-08-31`):

| stratum | rows | found in e-Postcard | carry a website | **website hit rate** |
|---|---:|---:|---:|---:|
| `990_N` | 6453 | 5573 (86.4%) | 1329 | **20.6%** |
| `not_required_to_file` | 2060 | 96 (4.7%) | 17 | **0.8%** |
| `UNKNOWN` | 129 | 18 (13.9%) | 8 | **6.2%** |

**And a website FIELD is not a website.** The funnel, every rung measured:

| rung | orgs |
|---|---:|
| organisations in shard-I's strata | 8,642 |
| carry a non-blank website field | 1,476 |
| the field actually parses as a URL | 1,019 |
| the host answered 2xx | 864 |
| the page carried an evidence-bearing sentence | 251 |
| **the page asserted Native CONTROL** | **15** |

Every no-content outcome is NAMED rather than left blank — 51 dead DNS, 40 TLS failures, 79 fields that were not URLs (`N/A` is the commonest value), 36 pages that served bytes but yielded no extractable text. *(shard H's rule: a truncated or script-rendered read must report why, never a bare negative. Zero reads hit the size cap this run.)*

**Robots audit** (prompted by shard H losing 22 hosts to a phantom block): this shard never used `urllib.robotparser`. `robots.txt` is fetched by curl with the **same UA** used for content and any non-200 yields an EMPTY rule set, i.e. ALLOWED. All **11** hosts recorded `ROBOTS_DISALLOW` were re-audited against their saved `robots.txt`: **11 genuine, 0 phantom** (six are `facebook.com`). No organisation was written off as closed because our own check lied.

**No domain was guessed.** Every URL probed came from the filer's own IRS return. Shard H's finding that a guessed domain returning 200 is fabrication with a status code next to it does not bite here because no candidate was ever generated from an organisation name.

**Decision:** are the remaining `990_N` organisations worth pursuing? **Recommendation: no further web sweep, and here is the arithmetic.** About four in five postcard filers publish no website at all; of the ones that do, roughly 14% of the pages fetched were dead, parked or refused. A second sweep buys a small number of thin pages at a large number of requests. **The cheap remaining routes are not web routes**: state charity registries (bulk, free, and they carry a purpose statement), and the group-exemption parent, which names the affiliation directly. Both are Tier-1 in `docs/PULL_DISCIPLINE.md` terms — bounded objects, not per-org fetches.

### 10c-bis. The structured-endpoint pass paid for itself, and here is the number

`docs/HIDDEN_DATA_TECHNIQUES.md` was adopted mid-run. It matters most for exactly this population: **635 of 831 sites had a RENDERED page too thin to decide anything from.**

| technique | sites where it produced data |
|---|---:|
| `meta_opengraph` | 669 |
| `feed_link_rel` | 293 |
| `wp_json_advertised_by_link_rel` | 219 |
| `jsonld_schema_org` | 195 |
| `data_attributes` | 108 |
| `wp_json_inferred_from_wp_content_paths` | 28 |
| `embedded_app_state_present` | 24 |
| `select_option_vocabulary` | 17 |
| `html_comment_carrying_native_language` | 4 |
| `published_google_sheet` | 4 |

Reading the structured routes out of bytes ALREADY retrieved cost **zero extra requests**. A bounded second pass then called 683 documented public endpoints (`/wp-json/wp/v2/pages`, `/wp-json/wp/v2/media`, `/feed/`) across 270 organisations and returned **2,419 PDF-library items, 1,261 feed items, 31 annual reports and 84 newsletter PDFs** — and added evidence on **55 organisations whose rendered page carried none at all.**

Worked example: **Samish Neighborhood Association** rendered a near-empty shell. `/wp-json/wp/v2/pages` returned 17 pages of text and the media library listed 64 documents — enough to resolve it, and it resolves to `placename_only`. The technique that produced the data is recorded per site in the `evidence` field, as the doc requires.

**Boundary, asserted not merely intended:** only documented public endpoints were requested. `structured_probe.py` carries a `FORBIDDEN` regex covering `/wp-admin`, `/admin`, `/.env`, `/.git`, `/staging`, backups and dumps, and it *raises* rather than skips. Nothing behind a login, no robots `Disallow` path, no `TERMS_STATED_RESTRICTIVE` source.

### 10c-ter. Newsletters — where small Native nonprofits actually publish

140 organisations probed, 127 readable. Channel counts:

| channel | orgs |
|---|---:|
| `facebook_only` | 77 |
| `wordpress_blog` | 54 |
| `own_site` | 22 |
| `mailchimp` | 20 |
| `wix` | 19 |
| `squarespace` | 10 |
| `constant_contact` | 1 |

**`facebook_only` is the largest single channel.** That is a finding for the funding and deals datasets: a bulletin that never leaves Facebook is invisible to every route Cedar currently runs, and `facebook.com/robots.txt` disallows `/` for `*`, so it is not harvestable. Depth and cadence are recorded; archives were NOT downloaded. File: `data/staging/np_harvest/newsletters_shard_i.jsonl`.

### 10d. `filing_req_cd = 14` is a 51-row seam the doc says is invisible

The dataset doc warns that *"tribal instrumentalities largely DO NOT file 990s (IRC §7871) — the LARGEST tribal institutions can be invisible here."* True in general. But **BMF `filing_req_cd = 14` is the governmental-instrumentality code, and 51 `np_orgs` rows carry it** — the instrumentalities that hold an EIN anyway. They include San Carlos Apache College, Seneca Nation Library, Seneca Nation of Indians Economic Development Company, Cherokee Nation Education Corporation, Kickapoo Nation School and Quileute Tribal School. They also include County of Apache and Indian River State College, so it is a seam, not a whitelist.

**Decision:** should `filing_req_cd = 14` become a named review stratum? **Recommendation: yes** — 51 rows is a one-sitting adjudication and it is the densest concentration of genuine tribal institutions anywhere in this dataset. Relatedly, **1,491 of the 2,060 `not_required_to_file` rows are churches** (`filing_req_cd = 06`), which the doc already excludes in principle but which still sit in the row count.

### 10e. 4,362 candidate nonprofit→spine links — record or mint?

**This is the architectural question and it is yours, not an agent's.** `data/spine/cedar_identity_register.csv` has 17 entity classes and **no nonprofit class**, while `np_orgs.csv` holds 12,764 organisations of which 1,423 (11.1%) carry a `cedar_uid`.

Shard I found that **every one of the 6,646 unkeyed `tribe_id_token_match` values resolves exactly to an existing `spine.handle`** — 4,362 of them in shard-I's strata. So the links are mechanically available today.

**They should not be minted, and the harvest is the reason why.** Of the candidates where a website could be read, **434 were CONTRADICTED by the organisation's own site** and only **6 were corroborated**. A token match is the Umatilla Electric shape: `PENOBSCOT COUNTY CONSERVATION ASSOCIATION` token-matches `TRBF-PNBSCT-00` and is a Maine sportsmen's club.

**Decision, three options:**

1. **Mint a `Native nonprofit` entity class and key all ~11,300.** Fast coverage; imports every place-name false positive into the master list, where `START_HERE.md` standing rule 1 says a laundered tier can never be un-laundered. **Not recommended.**
2. **Mint nothing; keep nonprofits keyed only by EIN, and let the spine reach them through `np_ein_uei_bridge.csv`.** Honest, but the bridge is **28 rows**, so in practice the nonprofit economy stays outside the entity layer.
3. **Mint a nonprofit class, but populate it only from RULED rows** — the 89 promotions already in `docs/NONPROFIT_CLASSIFICATION_RESEARCH_LOG.md`, the `native_entity` evidence rows above, the 51 `filing_req_cd = 14` instrumentalities, and whatever shard J's mission-text pass promotes. Every other row stays a candidate in `data/staging/np_harvest/candidate_spine_matches_shard_i.csv`. **Recommended.** It makes the class exist, so the dataset has somewhere to key to, without the entity layer inheriting an unadjudicated backlog.

Files: `data/staging/np_harvest/candidate_spine_matches_shard_i.csv` (4,362 rows, each with `corroboration` and a per-row recommendation), `shard_i.jsonl` (9,918 harvested rows), `README.md` (what is and is not a claim).


### 10f. `anc_ceiling_roster.csv` carries 4 scraper artefacts and 1 duplicate corporation — delete, or keep and label?

Found 2026-09-02 by `code/900_nr_hub_join.py` while joining the roster's
source-local `anc_id` scheme to the hub. 190 of 196 rows resolved to an active
`ANRC`/`ANVC` register entry. **Six did not, and four of them are not
corporations at all** — they are page furniture scraped from
`https://ancsa.lbblawyers.com/native-corporations.htm` (`confidence_tier = C`
on every roster row, `source` names the page):

| `corporation_name` as recorded | what it is |
|---|---|
| `A compilation of information about the Alaska Native Claims Settlement Act` | the page's own strapline |
| `Alaska Native Claims Settlement Act (ANCSA)` | a heading |
| `Native Corporations \| ANCSA Resource Center` | the page title |
| `Village and Urban Corporations` | a section heading |

The other two are **one corporation entered twice** — `The Thirteenth Regional
Corporation` and `The 13th Regional Corporation` — and it is a real ANC that
**Cedar's spine does not hold** (12 `ANRC` handles; the Thirteenth is not among
them). It carries 0 rows in `ancsa_filings_index.csv`, so nothing downstream
depends on it today.

Nothing was deleted. All six carry `entity_resolution_status = unresolved` and
a blank `cedar_uid`, and each is a row in
`review/nr_hub_join_unresolved_2026-09-02.csv` with its reason.

**Decision, and it is a row deletion so it is yours:**

1. **Delete the 4 artefacts** and de-duplicate the Thirteenth to one row. The
   roster is a shippable customer table whose grain is declared *"one row per
   Alaska Native Corporation"*, and four rows that are not corporations
   falsify that grain and inflate any per-ANC denominator by ~2%.
   **Recommended**, with the deletion recorded in the correction register.
2. **Keep all six and rely on the label.** Nothing is lost, but a buyer
   counting ANCs off this table over-counts unless they filter on a column the
   grain statement does not mention.

Separately, and not a deletion: **mint the Thirteenth Regional Corporation into
the spine** so the roster can key 191 of 192 real rows. It is an ANCSA
regional corporation for Alaska Natives resident outside Alaska; it has no
filings in Cedar and no money attached, so the mint is low-risk and can wait.

Files: `data/clean/anc_ceiling_roster.csv` (new columns `cedar_uid`,
`cedar_uid_basis`, `entity_resolution_status`),
`review/nr_hub_join_unresolved_2026-09-02.csv`.

---

## Native-owned business ↔ contracting crosswalk — 3 decisions (appended 2026-09-02, band 1000–1009)

Full write-up: `docs/NATIVE_BUSINESS_IDENTIFIER_CROSSWALK_LOG.md`.
Row-level evidence: `review/native_business_identifier_proposals_2026-09-02.csv`
(75 proposals, your inbox format, each with candidate UEIs, the dollars at
stake, and a `cage.dla.mil` protocol).

**Where it stands.** `business_entity_id` was populated on **4 of 2,393** rows.
**203 rows are now linked** to a federal contracting record across **169
distinct UEIs**: **$13.43B prime** (of which **$11.67B was already attributed**
to a Cedar entity and **$1.76B was not**), **$2.16B subawards**, plus $71.3M of
SAM FY2000–07 net-new. Nothing below is attributed until you rule.

**The route that worked was not the one anyone expected.** The tribal
directories publish **no** CAGE, UEI or DUNS — measured across all 249 raw
objects. The web probe of all 99 firm websites the directories published found
identifiers on **5 hosts**. What actually broke it open was
**`federal_contract_number`**, a column already in the table on 20 ASRC rows:
a printed PIID resolving to one UEI links **BROADLEAF, INUTEQ and VISTRONIX** —
the three firms the mandate names as unreachable by any name matcher.

### A. 59 tier-C/X promotions — a unique name with no geography behind it

Exactly one federal entity carries the name; the directory row carries no city
and no state, so nothing corroborates it. Held, published nowhere.
**Recommendation:** rule the *class* by dollar band. **30 of the 59 are under
$250K** — the cost of an error there is small and that is where the coverage
is. The **29 above** it are worth one lookup each; the largest are
`Seven Generations Architecture & Engineering` (Cherokee Nation → a Kalamazoo
MI recipient, **$240.3M**), `Fire Creek, LLC` ($99.7M, a Winnebago NE
recipient) and `DT-Trak Consulting` ($108.1M, Miller SD) — each a plausible
Native firm and each keyed to a state the certifying nation does not sit in.

### B. 8 ambiguous holds and 8 state conflicts — 16 firms, one CAGE lookup each

The holds are one directory name over 2–5 federal UEIs that do **not** share a
city, so they are not 8(a) successor entities (those merge automatically).
The conflicts are a same-name federal recipient in a different state; the veto
refused them and may be wrong wherever the directory printed a mailing address.
**Biggest single item:** `Arctic Slope Technical Services, Inc.` over 5 UEIs
spanning NM, CO, AK, AL and MD — the largest carrying **$12.0B** and also
trading as **`SIVUNIQ`**.

### C. THE POLICY ONE — a UEI on a firm named after a person

`business_name_is_person_name` is `1` on 280 directory rows and unknown on 327.

* **Your rule:** a firm's name is not PII even when the firm is named after its
  owner. A prior pass wrongly withheld 521 rows on that ground.
* **Cedar's coded policy** (`cedar_domain.INDIVIDUAL_NATIVE_WITHHELD_FIELDS`)
  is about the **identifier**, not the name: SAM's public entity search
  resolves a UEI to a name *and a street address*, so for a sole-proprietor
  firm the UEI is a pointer to that person's front door.

Both can be true, and this build did **not** decide between them. Every row
carries its identifier plus `identifier_publish_gate`; **35 crosswalk rows on
19 linked firms** are `WITHHOLD_PENDING_RULING` today.
**Decision:** does the UEI/CAGE of a firm whose legal name is a person's name
publish (a) always, (b) never, or (c) only where the firm is demonstrably
incorporated — an LLC/Inc suffix on the registered legal name?
**Recommendation:** (c). It keeps your rule about names intact and withholds
only the one field that resolves to a home address.

### FYI, not a decision — two things the 950–959 agent should see

1. **`code/953`'s name-only matcher and this one agree on 140 rows and
   disagree on 0**, which is reassuring but is *not* corroboration — both read
   the same federal tables (`docs/ASSERTION_LAYER.md`, evidence lineage).
   **But 6 of 953's `unique_name_match` rows contradict the directory's own
   recorded state** — e.g. `Arrowhead Contractors, LLC`, certified in North
   Carolina, keyed to a Louisiana recipient. Those 6 are in the conflicts file.
2. **`TBD-059` (Doyon) is 8 rows and 4 of them are prose, not firms** —
   `"Enjoy lunch at Kantishna Roadhouse"`, `"KRH Earns Best Wilderness Lodge"`,
   `", Klawock Island Ventures, and"`. Two more, Huna Totem Corporation and
   Klawock Heenya Corporation, are Doyon's **joint-venture partners in
   Na-Dena'**, not Doyon subsidiaries, yet carry
   `identity_scope = parent_asserted_subsidiary`. That is an ownership
   over-claim on the strongest evidence class in the dataset.

---

## APPENDED 2026-09-02 by the gaming web-harvest workstream (`code/980_gaming_web_harvest.py`)

### Is the Navajo Nation a `TERMS_STATED_RESTRICTIVE` source for its CASINO sites?

**Decision:** does the Navajo restriction cover the whole nation, or only
`navajoeconomy.org`?

**Why it is being asked.** `review/tribal_vendor_list_registry_2026-08-26.csv`
marks Navajo `TERMS_STATED_RESTRICTIVE`, and the quote that justifies it is a
copyright footer on **navajoeconomy.org** — *"(c) 2025, www.navajoeconomy.org.
All Rights Reserved."* The standing hard list in the workstream mandate names
eight nations and **Navajo is not one of them**.

This run excluded the nation **entirely** — the safe direction — and no request
of any kind was made. The cost is four properties and their nation-side pages:
**Fire Rock, Northern Edge, Flowing Water and Twin Arrows**, plus
`navajogaming.com` / `navajocasinos.com`.

**If the restriction is registry-wide (status quo):** those four properties stay
out of `gaming_web_harvest_observations.csv` permanently, and the exclusion is
already recorded per host as `EXCLUDED_TERMS_STATED_RESTRICTIVE`. Asking the
Nation is the route back in.
**If it covers only `navajoeconomy.org`:** the casino hosts become harvestable
on the next run; nothing else changes, because they were never touched.

**Recommendation:** rule it narrow to the vendor-directory source unless the
casino sites carry their own restrictive terms, and re-read those four sites'
terms pages before harvesting either way.

**A related error this run found and fixed.** `dancingeaglecasino.com` had been
placed in the restricted-host list as Navajo. **Dancing Eagle is Pueblo of
Laguna.** An over-broad restriction costs a nation its coverage just as surely
as a missed one costs the publisher their terms. Corrected in
`code/980_gaming_web_harvest.py`; no other misassignment found.

### FYI, not a decision — four tribal domains are compromised or dead

Recorded, never linked, never harvested from. All four should be marked in
`data/staging/cedar_web_map.csv`:

- **`mewuk.com`** (Tuolumne Band of Me-Wuk) — the **Tribal Gaming Agency** page
  carries injected SEO spam linking to Indonesian gambling sites at
  `103.179.73.92`. The design and title are the nation's own; the injection is
  not. This one is worth telling someone about.
- **`cahto.org`** (Cahto Tribe) — fully hijacked; `<title>` is *"Cahto: Situs
  Slot Online Terpercaya 2022"*. The tribe's real site is
  `cahtotribe-nsn.gov`, which fails TLS verification and was recovered only by
  a relaxed-TLS retry.
- **`theluckydogcasino.com`** (Skokomish) and **`desertrosecasino.com`**
  (Alturas Indian Rancheria) — both parked and **for sale** on HugeDomains.

Ten further hosts have simply **moved** (`cherokee.org → cherokee.gov`,
`lvpaiute.com → lvpaiute.gov`, `hoplandtribe.com → hbpi.gov`,
`southwindcasino.com → rockandbrewscasinobraman.com`, …). Those are findings,
not refusals. Full list in `docs/GAMING_WEB_HARVEST_LOG.md`.

---

## NEST-1 — Ho-Chunk: repoint five ledger rows from the Ho-Chunk Nation of Wisconsin to the Winnebago Tribe of Nebraska?

*Raised 2026-09-02 by workstream `nest` (`code/1072_tribally_owned_enterprises.py`).
A recommendation, not an edit: these rows belong to another workstream's table.*

**Your own ruling is already the answer** — *"Ho-Chunk means a sub-hub, or
Winnebago casino is a sub-hub. And then the hub is Winnebago Tribe."* This item
exists only to say which rows it applies to and what NEST found independently.

**What NEST holds, from the parents' own published company lists:**

| enterprise | owner in NEST | source |
|---|---|---|
| Ho-Chunk Inc | Winnebago (`TRBF-WNNBGO-00`) | `hochunkinc.com` |
| Ho-Chunk Farms | Winnebago | `hochunkinc.com` |
| Ho-Chunk Trading Group | Winnebago | `hochunktrading.com` |
| Ho-Chunk Construction Group | Winnebago | `hochunkconstructiongroup.com` |
| HoChunk Community Capital (CDFI) | Winnebago | `hochunkcdfi.org` — already `CDFI-HCHNKC-00` in the spine |

**What the ledger holds** (`review/named_collision_families_2026-09-02.csv`):
`Ho Chunk Inc` (UEI `DMA6EKCMAPB7`), `HO-CHUNK FARMS` (CAGE `7CE83`) and
`HO-CHUNK CONSTRUCTION MANAGEMENT` (CAGE `8APB4`) are keyed to **Ho-Chunk Nation
of Wisconsin** (`TRBF-HOCHNK-00`) — a different federally recognized tribe that
shares one word — and separately `Ho-Chunk Nation` CAGE `3VFL3`, **tier A**, is
keyed to Winnebago. The contamination runs in both directions.

**Why NEST did not simply match its way to this.** The naive version of its
"a named firm that resolves to a Cedar hub is not that hub's subsidiary" guard
**held Ho-Chunk, Inc. and lost the row**, because `norm()` strips `Inc` and the
name then equals the spine's `Ho-Chunk`. The rule that fixed it is structural
and general: **a GOVERNMENT-class hub can never BE somebody else's subsidiary,
so a government-class name match is always the collision and never the
identity.**

**The question:** repoint the three Winnebago-company rows to `TRBF-WNNBGO-00`,
and re-examine the tier-A `Ho-Chunk Nation` CAGE `3VFL3` row keyed to Winnebago,
which looks like the same collision inverted.

- **Yes** → the ledger agrees with what both nations publish about themselves,
  and dollars stop crossing between two tribes.
- **No** → NEST and the ledger will disagree about the same five firms, and a
  customer joining the two datasets on `cedar_uid` sees it.

**Verification protocol, your own (ENTITY_MATCH_RULES rule 13):** the addresses.
Ho-Chunk, Inc. is Winnebago, Nebraska; the Ho-Chunk Nation is Black River Falls,
Wisconsin. Rung 1 settles it.

> **PARTLY CLOSED, same day.** The integrator applied the repoint in
> `prime_contracts.csv`: **21 rows on UEIs `DMA6EKCMAPB7` and `S4LTC7CL8RW7`
> moved to Winnebago**, each asserted to carry `recipient_city_name =
> WINNEBAGO` before being touched, and Wisconsin keeps its 17 Black River Falls
> rows — rung 1 run as a precondition rather than as a spot check. NEST and
> `prime_contracts` now agree.
> **Still open:** the ledger rows themselves (`cedar_identifier_ledger_final.csv`),
> and the tier-A `Ho-Chunk Nation` CAGE `3VFL3` row keyed to Winnebago, which
> looks like the same collision inverted and which no pass has yet examined.

---

## TD-1 — MSRB EMMA: buy the licence, ask for permission, or drop the source?
*Appended 2026-09-02 by the tribal-debt workstream (`code/1082_tribal_debt_holdings_disclosure.py`). Full evidence: `docs/TRIBAL_DEBT_HOLDINGS_BUILD_LOG.md`.*

**Decision:** EMMA is the largest unexploited source in this project and it is
closed by its Terms of Use, not by robots. Pick one: (a) buy access, (b) write
and ask, (c) record it as permanently out of scope and stop re-opening it.

**This is not the same question as 2026-08-05, because the clause is worse than
the record said.** Re-read verbatim today from
`https://emma.msrb.org/AboutEmma/UserAgreement` (cached):

1. **It bars the OUTPUT, not just the method** — *"you will not: use Content or
   Services to develop or create a database to be sold, leased, furnished,
   licensed or otherwise exploited or made available (either commercially **or
   free of charge**)."* Releasing it free is not a way round.
2. **It names MANUAL collection** — *"...or similar automated or data gathering
   or extraction method, **or any manual process**..."* The August log quoted
   only the automated half, which left the impression a human could read the
   documents in the meantime. **There is no hand-collection workaround.**
3. **A SECOND licensor sits on top** — CUSIP Global Services / ABA: *"Any use by
   you outside of the clearing and settlement of transactions requires a license
   from CGS, along with an associated fee based on usage."* An MSRB licence
   alone does not clear CUSIPs. Cost both.

**What it is worth.** ~95 tribal issuer records across ~70 tribal governments
are already enumerated by name (`docs/TRIBAL_DEBT_BUILD_LOG.md`). For the
gaming-authority subset, the **annual audited financials carry facility-level
gaming revenue** — the figure `gaming` records as `SOURCE_DOES_NOT_PUBLISH` on
776 of 787 rows *(**GAMING-DENOMINATOR-2026-09-02:** `gaming_facilities.csv` holds **787 ROWS, not 787 facilities** — 16 rows' NAMES say no casino (7 exactly, 9 like `Grand Canyon West - no casino`) and 57 extra rows sit across the same-tribe duplicate groups, so **771 facility rows and 714 distinct properties**. Five denominators circulated on 2026-09-02 — 787, 780, 734, 727, 714 — and only the last is the property count. Authority: `code/846_session_audit.py::_denom`; derive it with `py -3 code/1116_ruling_propagation_2026_09_02.py derive`.)*. Nothing else Cedar can reach moves that number at scale.

**If (a) BUY:** the tribal bond-finance dataset becomes buildable and the gaming
revenue gap starts closing. Two licences to price, not one.
**If (b) ASK:** free, and the agreement states its own exception — *"unless
otherwise authorized by the MSRB"* — naming where to write (MSRB, 1300 I Street
NW, Suite 1000, Washington DC 20005, Attn: External Relations). Cedar's standing
principle is that asking is the route back in. **Recommended first move**: it
costs a letter and it makes (a) unnecessary if it lands.
**If (c) DROP:** say so once, in `docs/PUBLICATION_POLICY.md`, so no fourth
session re-derives the same refusal. Three have now.

**Not a route, and worth writing down so nobody tries it:** the underwriter /
conduit-issuer path is real under the TERMS-SCOPE ruling (a third party's filing
is not the restricted entity's), but it **cuts the other way for EMMA
continuing disclosure specifically**, because those documents are filed *by the
obligor*. For the eight hard-listed sources their own filings stay excluded.

---

## EL-1. Eight tier-A identifier rows whose legal name is ANOTHER nation's official name — $3.68M, five of them PUBLISHED

*Appended 2026-09-02 by the `_entity_layer` pass.
Detector: `code/1099_crosstribe_legalname_audit.py`.
Full register with evidence: `review/ledger_crossgov_name_collisions_2026-09-02.csv`.*

**Decision:** for each row below, repoint the identifier to the proposed nation,
or confirm the current key and say why.

Nothing has been repointed. The ledger carries a new
`crossgov_name_collision_*` flag family and no `tribe_id`, tier or method was
touched (`ENTITY_MATCH_RULES` rule 8; the Bristol Bay precedent for anything
that keys a dollar).

**The predicate**, so you can judge the detector and not just the rows: the row
is keyed to a government-class entity; its `legal_business_name` carries **no
legal-form token** (so it presents as a government, not a firm — this is what
keeps the CORRECT `Ho-Chunk, Inc.` rows out); the keyed entity's own names leave
a residue; and exactly one OTHER government's official names account for the
whole name. 13 rows out of 5,836 government-keyed ledger rows.

| id | tier / method | keyed now | the name on the row | proposed | evidence |
|---|---|---|---|---|---|
| UEI `HLTFBD3FTDG8` | A `hand` | Fort Sill-Chiricahua-Warm Springs-Apache (OK) | "Confederated Tribes Of Warm Springs Reservation Of Oregon" | `TRBF-WRMSPR-00` (OR) | **285 prime rows, $3,552,567, `recipient_state_code = OR` on 285 of 285** |
| UEI `LWRAHAFNKQ13` | A `hand` | Santee Sioux (NE) | "Flandreau Santee Sioux Tribe" | `TRBF-FLANDR-00` (SD) | 7 rows, $51,336 |
| CAGE `50WN1` | A `bgov_manual` | Santee Sioux (NE) | "Flandreau Santee Sioux Tribe" | `TRBF-FLANDR-00` (SD) | 4 rows, $51,336; registration state SD |
| CAGE `4AD60` | A `bgov_manual` | Santee Sioux (NE) | "Flandreau Santee Sioux Tribe" | `TRBF-FLANDR-00` (SD) | 6 rows, $24,521; registration state SD |
| CAGE `4XH62` | A `bgov_manual` | Yavapai-Apache (AZ) | "Chignik Lagoon, Native Village Of" | `AKNF-CGNKLG-00-…` (AK) | registration state **AK**; an Alaska Native Village keyed to an Arizona tribe |
| CAGE `3VFL3` | A `bgov_manual` | Winnebago (NE) | "Ho-Chunk Nation" | `TRBF-HOCHNK-00` (WI) | registration state **WI**; source row `entity_crosswalk_bgov.csv` XW-0729 is the ONLY Wisconsin row among Winnebago's 27, and it sets `Subsidiary_Flag = 1` — **a federally recognized tribe cannot be a subsidiary of another federally recognized tribe** |
| CAGE `3XGD7` | A `bgov_manual` | Sac and Fox Nation (OK) | "Sac & Fox Nation Of Missouri In Kansas And Nebraska" | `TRBF-SCFXMO-00` (KS) | registration state KS |
| UEI `PHLGX6MG6UK1` | B `cluster_v3` | Shoshone-Paiute (NV) | "ELY SHOSHONE TRIBE" | `TRBF-ELYTNV-00` (NV) | both NV — **the address cannot separate them**; flagged, not proposed |

**Five of the eight are in `cedar_publishable_identifiers.csv`**, so Cedar is
today publishing "this CAGE belongs to that nation" for each of them.

**One case is the opposite and needs no ruling, only a spine edit.** UEI
`H1ZEEZK2D6B3`, `"San Juan Pueblo Tribal Council"`, is keyed to **Ohkay Owingeh
(NM) and that is CORRECT** — Ohkay Owingeh *is* the renamed San Juan Pueblo, and
113 of 113 awards are in New Mexico. It only looks like a collision because the
spine does not carry `San Juan Pueblo` in Ohkay Owingeh's `aliases`, so a former
name reads as a foreign one, and the apparent rival `TRBF-SNJUAN-00` is the San
Juan **Southern Paiute** Tribe of **Arizona**. **Ask: add the alias?**

**If YES on a row:** the identifier and its prime rows move to the proposed
nation; `$3.55M` of the total is the Warm Springs row alone.
**If NO:** say which rung of `ENTITY_MATCH_RULES` rule 13 answers it, so the
detector can learn the exception rather than re-raise it next quarter.

---

## EL-2. `Laulima Government Solutions, LLC` has two declared owners

**Decision:** is this a joint venture (two parents, both correct) or is one side
wrong?

- `entity_relationships.csv`, tier A: owned by **Bering Straits Native
  Corporation** — *"Ruled by Elijah 2026-08-06: re-attributed to Bering Straits
  Native Corporation (matched by exact); the earlier claim was wrong."*
- `nest_enterprises.csv`, shard-H `parent_declared_subsidiary_list`: a
  subsidiary of **Alaka'ina Foundation**, source `http://beringalakaina.com/`.

**The host name contains both.** `ENTITY_MATCH_RULES` rule 11: a JV genuinely
has two parents. No link was written and neither side was altered.
File: `review/entity_rel_nest_owner_conflicts_2026-09-02.csv`.

**If JV:** NEST should carry it as `relation_class = affiliation`, not ownership.
**If one side wrong:** name which, and the other is withdrawn.

---

## EL-3. 523 rows of `native_owned_businesses` are an unreviewed page scrape, and 178 of them are people's names

**Decision:** ratify the publish hold, or name a review route.

`code/1070`'s sweep staged 1,106 rows. The 583 OWNERSHIP rows went to NEST,
which **refused 229 of them** as *"unreviewed HTML heading/anchor scrape"* —
the block yields page furniture and **natural persons' names**, and
`docs/NEST_BUILD_LOG.md` makes that a hard rule. The 523 RELATIONSHIP rows were
merged into `native_owned_businesses.csv` and **the same refusal was never
applied to them**. Measured on the live table before this pass:

- all 523 carry the caveat *"HTML heading/anchor scrape — not a table; review
  before resolving"* in their own `verification_basis`;
- all 523 read `business_name_is_person_name = -1` — **1070 hard-codes it; the
  detector in `code/330` was never run on them**;
- all 523 read `publishable = Y`.

Three of the first three inspected: `"Tribal Enterprise Directory"` (the page's
own heading), `"Rebecca Naragon"` (a person), `"Akwesasne Farmers Market"` (a
real enterprise).

`code/1100` ran `looks_like_person()` over exactly those 523: **178 ARE a
natural person's name, 87 are not, 258 undecidable** — and set
`publish_hold = Y` with `publishable = N` on all 523, preserving the prior value
in `publishable_before_1100`. Reversible by one column copy.

**If RATIFY:** 523 rows stop publishing; the directory's publishable count falls
by 523 and its person-name exposure goes to zero on this family.
**If REVIEW:** the 87 the detector cleared are the cheapest re-entry, and USET's
directory would need a table parse rather than a heading scrape.


---

<!-- BEGIN DEALS-MERGE-1088 -->
## DM-1. Six real deals are sitting in the refusal register because the PARTY is wrong, not the deal

**Decision:** authorise a party re-derivation pass on the 33
`G5_PARTY_IS_PUBLISHER_NOT_TRANSACTOR` refusals, or leave them refused.

`code/1088_merge_staged_deals.py` refused 33 tribal-press candidates because the
`Native_Party` assigned by the screen is the PUBLISHER of the page, not the
transactor. Most of those 33 are noise — a statewide news aggregator attributed
Dell's $9.7B contract, Anthropic's $200M contract and the Coast Guard's $25B
acquisition programme to the Alaska village of **Craig**, and a South Carolina
library friends group reached a tier-A Indian Country deal queue on the token
`Pine Ridge`.

**But at least six carry a real Indian Country transaction under a wrong
party**, and refusing them loses the deal along with the error:

| the transaction, as the source states it | party the screen assigned | party the sentence names |
|---|---|---|
| Mille Lacs Corporate Ventures acquires 2020 Brand Solutions | Minnesota Indian Gaming Association | Mille Lacs Band of Ojibwe |
| MG2 Tribal Energy, a JV with Geronimo Energy, signs a PPA | Minnesota Indian Gaming Association | Mesa Grande Band of Mission Indians |
| Navajo Nation acquires Goulding's Lodge, Monument Valley | Coalition of Large Tribes | Navajo Nation |
| Savoonga Reindeer Commercial Company EDA-funded meat plant | Brevig Mission | Savoonga / SRCC |
| Kawerak Inc. EESS three-year ANEP grant | Brevig Mission | Kawerak Inc. |
| Staraaya, a joint venture with KANA | Alaska Federation of Natives | KANA (Kodiak Area Native Association) |

**If AUTHORISE:** each row's party is re-derived from the source sentence and
re-run through the same gates; expect roughly 6 rows, none large, all with a
live source link. The cost is that the party then rests on a sentence read
rather than on the publisher prior — which is what the rest of this dataset
already does.
**If LEAVE:** all 33 stay whole in `review/deals_1088_refusals.csv` with their
evidence quotes, and Cedar publishes 6 fewer real transactions rather than 6
wrong parties. This is the safer answer and it is not obviously the right one.

---

## DM-2. Two ownership changes nobody announced carry a fiscal-year WINDOW, not a date

**Decision:** ratify shipping them with a blank `Event_Date`, or hold them out
of the ledger until a date is found.

Merged as `IDOBS-2021-001` **WHPacific, Inc.** (NANA Regional Corporation ->
NV5 Global, FY2019->FY2021) and `IDOBS-2019-001` **Clarus Fluid Intelligence,
LLC** (Koniag side -> Chestnut Park, FY2017->FY2019). Neither appears in any
Cedar source as an announcement. Both are visible only because the subawardee's
UEI held constant while its declared parent did not — the route you described
as *"an ownership change in the contracting data with no published deal is a
deal Cedar can report."*

The tension: `docs/methodology/deals.md` says **never write a row whose date is
not in retrieved evidence**, and a run boundary is a gap, not a date. They are
currently shipped with `Event_Date` **blank**, `Event_Year` set to the window's
end, and `Date_Basis` reading *"FISCAL-YEAR WINDOW, NOT A DATE."*
`Verification_Status` says in full: *"UNVERIFIED AGAINST ANY PUBLISHED
ANNOUNCEMENT — this is an observation Cedar made, not a claim a source
published."* Five rows in the ledger already carry a blank `Event_Date`.

**If RATIFY:** Cedar reports two transactions nobody else has, and the ledger
gains a small class of rows whose date is a window. `code/1088 verify` exits 1
if such a row ever loses its `Date_Basis` explanation.
**If HOLD:** they move to a candidate register and Cedar publishes nothing that
carries a window where a buyer expects a date.

---

## DM-3. The terms release yielded ONE deal, not three — confirm the framing

**Decision:** confirm, or say the release should be described differently.

Your `TERMS-SCOPE` ruling (a restriction binds what the restricted entity
published, not a third party's SEC filing about them) released three held EDGAR
families. Worked through:

* **NANA** — a real deal. Trilogy Metals' 10-K discloses Ambler Metals LLC, a
  50/50 JV completed 2020-02-11, South32 subscribing US$145,000,000. **Merged.**
* **Southern Ute** — refused, and **not on terms**. The $14,452 thousand is the
  gross **carrying amount** of an amortising intangible on MACH Natural
  Resources' balance sheet, not a purchase price, and the filing gives no
  transaction date. The value and date rules refuse it; terms no longer do.
* **Chickasaw** — refused. AP Gaming Holdco names the Nation in market context.
  There is no transaction in the filing to release.

The framing that matters: **"three families released, one deal found."** A
report saying the ruling unblocked three deals would be wrong, and it is the
kind of wrong that is hard to catch later.
<!-- END DEALS-MERGE-1088 -->

---

## PR29-1. The `native-owned-businesses` collection does not contain `native_owned_businesses.csv` — and the product publishes the resulting row count

*Appended 2026-09-02 by workstream PR29-LOOP (the standing Codex loop). Declared in ADR-018.
Evidence: `docs/CODEX_REVIEW_LOG.md`, PR #29 round 3.*

### The decision

**Do we widen the `native-owned-businesses` collection to claim the four
business-directory tables — and accept that the dataset stops being READY
until they carry a grain and a key?**

This is an owner/integrator call and not an agent's, because it moves a
dataset's readiness and it touches `500_build_architecture_map.py`,
`512_build_dataset_contracts.py` and `518_dataset_readiness.py`, all
integrator-owned.

### What is true today, measured 2026-09-02

The product repo currently ships two numbers for one dataset, in two files in
the same directory:

    data/cedar/samples/README.md            owned -> native_owned_businesses.csv, 2,916 rows
    data/cedar/collection_descriptors.json  owned -> "rows_label": "1,657 rows"

`500.COLLECTIONS` matches this collection with
`^(individual_native|tribal_certification)`. The namesake directory matches
neither branch, so the contract claims six `individual_native_*` tables
(1,657 rows — firms owned by individual *people*) and the customer's sample is
drawn from the harmonised directory (2,916 rows, 21 certifying authorities —
firms certified or listed by *nations*). **These are two different relations,
and only one of them is in the contract.**

It has been a known orphan since 2026-09-01 —
`code/730_ws4_grain_money_conservation.py:852`, under
`contract_orphan_shippable = 6`, attributed to "the workstreams that
registered them". The attribution was right; nobody owned the consequence.

**The readiness claim is the serious half.** `native-owned-businesses` is
READY on `c4_identity_path = 100% keyed` and `c1_grain = 6/6`, both measured
across the six tables that exclude the directory. On the directory itself:

| | |
|---|---:|
| rows | 2,916 |
| `business_entity_id` filled | **4 (0.1%)** |
| `nation_id` filled | 2,725 (93.4%) |
| `certifying_authority_entity_id` filled | 2,767 (94.9%) |
| declared grain | **UNSTATED** |
| declared primary key | **none** |

The four tables that would join the collection:

| table | rows | grain declared | key declared |
|---|---:|---|---|
| `native_owned_businesses.csv` | 2,916 | no | no |
| `native_business_contract_links.csv` | 2,393 | no | no |
| `native_business_identifier_crosswalk.csv` | 481 | no | no |
| `native_business_contracting_by_nation.csv` | 18 | no | no |

**Note a second defect visible in that table.**
`docs/NATIVE_BUSINESS_IDENTIFIER_CROSSWALK_LOG.md` states
`native_business_contract_links.csv` as **one row per directory row**. It has
2,393 rows and the directory now has 2,916, so **523 directory rows have no
link row** and the declared invariant is already broken by the directory's own
growth. That is true whichever way this decision goes.

### The consequences of each answer

**WIDEN (claim all four).** The collection becomes what its name says and the
product's row count stops contradicting its own sample. `native-owned-businesses`
goes **READY → BLOCKED** until grain and keys are declared for four tables and
`c4` is re-measured on a table whose business key is 0.1% filled — expect the
`100% keyed` line to fall a long way. The `affiliated_with` relation
`docs/PUBLICATION_POLICY.md` argues for keys to `nation_id` at 93.4%, so the
honest C4 statement is probably about the nation, not the business, and that
may need its own ruling.

**DO NOT WIDEN (keep the six individual-firm tables).** Then the collection is
misnamed and the sample is wrong: `770.FLAGSHIP` must be repointed away from
`native_owned_businesses.csv`, and the directory needs its own collection —
which is arguably the truer shape anyway, since it is the same
certified-vs-owned distinction that already justified splitting `nest` out as
a separate collection rather than merging it here.

**A third option, and it may be the best one.** Make the directory its own
collection (`certified-businesses` or similar) alongside `nest` and the
individual-firm set, on exactly the `500.COLLECTIONS` reasoning that kept
`nest` separate: *certified or listed by a nation* is a different relation
from *owned by a nation* and from *owned by an individual person*. Three
relations, three collections, no collection carrying a table it does not
describe.

### What is already in place, so nothing ships wrong while this waits

`760_collection_descriptors.py` (ADR-018) now refuses to publish a row count
its own sample contradicts. It marks the dataset BLOCKED with three measured
blockers in `cedar.blockers` — the count mismatch, `C4 identity path`
(`business_entity_id` on 4 of 2,916 rows) and `C1 grain UNSTATED`. `verify`
exits 1 and `selftest` carries three fixtures that prove the check fires.
**The status reverts by itself the moment the collection is settled** —
whichever way it is settled — so this item blocks nothing except the dataset's
own READY flag.

> **CORRECTED the same day, and the correction is evidence for this item.**
> This paragraph first said 760 "emits the union of both declarations (4,573
> rows)". Codex refused that on PR #29 round 3 and was right: summing 1,657
> and 2,916 asserts the two sets are disjoint rows of one dataset, which
> nothing establishes, and `rows_label` is the field the product renders while
> the qualification sat in a sibling file. **No count is published now** —
> `rows_label` reads `row count unresolved` and the two components ship
> separately, unadded.
>
> **Measuring the disjointness then found the fact that should decide this
> item.** Between the sets they are nearly disjoint — 10 shared firm names
> against the directory's 2,738. But `1,657` is itself a sum over **five
> different grains**: 45 firms, 324 firm-**years** (38 distinct firms), 335
> verifications, **the same 335 firms again** in a candidates table sharing
> all 335 `(name, uei)` keys and its full column set, 613 rows of a published
> **cross-tabulation** (`cell_type`, `dimension_1`, `n_firms` — not firms at
> all), and 5 pairs.
>
> **So the six tables now in this collection are not one dataset either.**
> That reframes the decision: the question is not only whether to add the
> directory, but whether a collection whose row count double-counts a table
> and includes an aggregate cross-tab should be shipping as READY at all.
> The third option below — three relations, three collections — gets stronger
> with this measurement, and a fourth is now visible: the individual-firm set
> may need to shed `individual_native_verification_candidates.csv` (a
> superseded input, not a customer table) and
> `individual_native_firm_contracts_published.csv` (an aggregate, not a row
> grain).

---

## TD-2 — PACER: buy the filings behind nine named tribal-debt dockets?
*Appended 2026-09-02 by the tribal-debt court workstream (`code/1110_tribal_debt_court_distress.py`). Full evidence: `docs/TRIBAL_DEBT_COURT_DISTRESS_BUILD_LOG.md`.*

**Decision:** the free CourtListener corpus gives us the *existence* of these
cases and, where an opinion was published, the court's own words. It does not
give us the **complaints, the indentures filed as exhibits, or the settlement
terms**. Those are on PACER at $0.10/page, capped at $3.00 per document.

**This is not a repeat of TD-1.** EMMA is closed by its terms at any price
short of a licence negotiation. PACER is simply **priced**, it is a federal
government service, and there is no terms problem at all with a document
obtained from it — `docs/PUBLICATION_POLICY.md` `TERMS-SCOPE`, *"the
distinction is authorship, not subject matter"*: a court filing is the court's
record.

**What it would buy, against named docket numbers.** These are the nine
dockets already staged in `data/staging/tribal_debt_court_dockets.csv`; the
first three are the ones that would move the dataset:

| docket | court | filed | why it matters |
|---|---|---|---|
| `1:21-cv-00177` | D.R.I. | 2021-04-20 | `U.S. Bank v. Mashantucket Pequot Gaming Enterprise` — **the only court record anywhere in Cedar of the Foxwoods obligor**, and Mashantucket is a `1082` holdings obligor. No opinion was published |
| `1:14-cv-01044` | E.D. Cal. | 2014-07-02 | `Bank of The Sierra v. Picayune Rancheria of the Chukchansi Indians` — contemporaneous with the Chukchansi noteholder distress, and the only federal docket on it |
| `5:12-cv-01278` | C.D. Cal. | 2012-08-01 | `Wells Fargo Bank NA v. Cabazon Band of Mission Indians` — Cabazon is a `1082` holdings obligor and the party array names `East Valley Tourist Development Authority`, its borrowing instrumentality |
| `3:01-cv-04125` | N.D. Cal. | 2001-11-05 | `Sonoma Falls Developers v. Dry Creek Rancheria` — Dry Creek is River Rock's nation, a `1082` obligor |
| `3:09-cv-00768` · `3:12-cv-00255` · `3:13-cv-00372` | W.D. Wis. | 2009–2013 | the Lake of the Torches trio. We already hold the published opinions; the filings would add the indenture itself |
| `1:10-cv-01039` | E.D. Wis. | 2010-11-19 | `Wells Fargo Bank NA v. Sokaogon Chippewa Community` — the Mole Lake sibling of Lake of the Torches, same trustee, same instrument shape |
| `1:20-cv-00183` | E.D. Cal. | 2020-02-04 | `Picayune Rancheria v. Goldenwise Capital Management` — the nation as **plaintiff**; lower value |

**If BUY:** budget is small and boundable — a docket sheet plus the complaint
and a handful of exhibits is single-digit dollars per case, so the whole list is
plausibly under $100. PACER also waives fees below $30/quarter, which may cover
a first pass at zero. The gain is the **instrument** — an indenture or credit
agreement filed as an exhibit is the document this whole workstream keeps saying
to quote, and we currently quote courts describing instruments rather than the
instruments themselves.

**If DON'T:** the table stays as it is, which is honest but thin: **32 events,
9 dockets, nothing after 2017, and only two rows that are a court holding
anything.** Say so once here so a later session does not re-derive the same
gap.

**A cheaper half-measure worth knowing about.** RECAP is crowd-sourced: buying a
document through the RECAP browser extension contributes it to the free archive,
so the purchase is not only ours. That is a reason to prefer PACER-via-RECAP
over a bare PACER account if this is approved.

### Also recorded here, because it cost time this session

**The mandate for this pass said `COURTLISTENER_API_TOKEN` "has never been
used." It had been** — `code/366` spent **112 requests on 2026-08-27**. The rate
limit (5/min, 50/hr, 125/day) is **per token, not per script**, so `1110` now
appends to `366`'s ledger rather than opening its own. Any third script on
CourtListener must do the same, or all three will collect 429s while each
believes it has a full budget.

<!-- BEGIN QM-QUARANTINE -->
---

## QM-1. The CAGE leg of the quarantine — $3.61B, measured for the first time and deliberately NOT touched

**Decision:** may an agent adjudicate the `cage_exact` leg the way `1079`
adjudicated the UEI leg, or does it wait for you?

**What is there.** CDR-11 measured UEI ledger rows. `40_build_prime_contracts.py`
keys on three legs. The two nobody had measured:

| leg | prime rows | obligations |
|---|---:|---:|
| `cage_exact` on a quarantined CAGE ledger row | 14,149 | $7,252,015,101 |
| `parent_uei` on a quarantined UEI ledger row | 41,055 | $489,839,872 |

*(Two named families have since been repaired out of that CAGE total on a
second, independent confirmation — North Wind / LBYD and Copper River — leaving
502 identifiers and $3,536,050,157 open.)*

`need_v6` — the method START_HERE records at **6.5% accuracy** — lives almost
entirely on this leg: 838 tier-B CAGE rows. It put 60+ CAGE codes on
`TRBF-LUMBEE-00`, the Lumbee Tribe of **North** Carolina, whose registered
names include `NORTH WIND …` ×30, `GSI NORTH AMERICA`, `MERCEDES-BENZ RESEARCH
& DEVELOPMENT NORTH AMERICA`, `KATMAI NORTH AMERICA`, `NORTH ISLAND CORP`,
`NORTH VALLEY CARING SERVICES`, `TDX NORTH SLOPE GENERATING` and `CAROLINA
PLACE APARTMENTS`. The token is `north`.

502 of those identifiers, $3,536,050,157, ran the full seven-rung ladder and
came back WITHDRAW or REPOINT. They were downgraded to HOLD **only** because
the CAGE leg was outside the declared scope of that pass. They are in
`review/1079_owner_holds_2026-09-02.csv` with their evidence and their basis.

**Consequence of each answer.** *Go* — another ~$3.5B moves from a discredited
attribution to honestly unattributed or to a repointed owner, on evidence that
is already gathered and already written down. *Wait* — the flag
(`identifier_ruling_quarantined = 'Y'`) means no consumer can mistake it for a
verified attribution in the meantime, so nothing is being published as true
that isn't. Cost of waiting is zero; cost of going is one more pass.

---

## QM-2. Three big holds that one look at an address or a website would settle

All three survived the ladder and are attributed **today**. Each is one rung-1
or rung-2 check away (`docs/ENTITY_MATCH_RULES.md` rule 13).

| firm | keyed to | $ | why it is held |
|---|---|---:|---|
| `GREAT HILL SOLUTIONS, LLC` | Golden Hill Paugussett | $549.8M | the only shared word is `hill` |
| `ARCTIC SLOPE MISSION SERVICES LLC` | **Iñupiat** (`AKNF-INPTAS-00-ARCSLO`, the Native Village) | $480.3M | the `ALASKA_VILLAGE_GOVERNMENT_VS_VILLAGE_CORPORATION` family — rule 12 says suspect the PARENT row: this is almost certainly Arctic Slope Regional Corporation, not the village |
| `AMERICAN EAGLE PROTECTIVE SERVICES CORP` | Native Village of Eagle | $450.5M | a Texas security firm on the trap token `eagle`; held only because it declares itself as its own parent |
| `KUPONO GOVERNMENT SERVICES, LLC` | Barrow | $351.0M | an NHO caught by the `government` token in *Native Village of Barrow Inupiat Traditional **Government*** |

**Consequence.** These four alone are $1.83B currently attributed on evidence
Cedar itself calls no evidence.

---

## QM-3. A hub whose whole name is one ordinary English word is still unguarded

**Decision:** should a single-token hub be barred from winning a name-only
match at all?

`MARSHALL COMMUNICATIONS CORP` — $336.3M — is **KEPT** on the Native Village of
Marshall, because rule 7's residue test accepts it (`marshall` is the hub's
entire distinctive name) and the new fragment rule cannot fire, needing a
second token to be a fragment of. Meanwhile the firm's FPDS-declared parent is
`MISSION SOLUTIONS GROUP INC`, observed **1,050 times**, resolving to no hub at
all.

It is defensible under Cedar's written rules and it is probably wrong. A wider
automatic rule would also strike `CHUGACH TECHNICAL SOLUTIONS` → Chugach and
`KONIAG MANAGEMENT SOLUTIONS` → Koniag, which are right — the difference is
that `chugach` and `koniag` are Alutiiq words and `marshall` is a surname, and
that difference is exactly rule 14's *"the names carry language"*, which no
structural predicate in this repo can currently express.

**Consequence.** *Rule it by hand* — one ruling, $336.3M, and the class stays
small. *Automate it* — needs a language signal Cedar does not have yet, and it
would break correct ANC links on the way.
---

## QM-4. Copper River: the right owner, found — and $1.5B still not attributed to them

**Decision:** who finishes it, and does the Native Village of Eyak get a ruled
ledger row?

**The evidence is as good as this project gets.** `code/1111_copper_river_attribution.py`
ran your ladder to rung 2 and the website says it outright —
`copperrivermc.com`, verbatim: *"Owned by the Native Village of Eyak, the
Copper River Family of Companies are a collection of both current and graduated
Small Business Administration (SBA) 8(a) Certified entities"*. Two other
readings agree it is **not** Barrow, Kluti Kaah or Seldovia: the family declares
`ALASKA NATIVE GOVERNMENT SERVICES, LLC` as parent and ultimate parent and sits
in Anchorage, and it shares zero UEIs with the Eyak **Corporation** family in
Dulles VA. Two Eyak entities in Cordova, and the website names the **tribe**.

**But the table does not say so.** Measured on the live file after every pass:

| who touched the row | `tribe_id` | rows | obligations |
|---|---|---:|---:|
| 1079 withdrew it from a wrong hub | *(blank)* | 2,546 | $1,028,280,369.01 |
| 1111 wrote `canonical_name` + `cedar_uid` = Eyak | *(blank)* | 1,720 | $471,401,841.02 |
| neither | *(blank)* | 22 | $12,872,336.90 |
| 1111 renamed it, `tribe_id` still Seldovia | `ANVC-SLDVSS-00` | 6 | $410,841.50 |

`confidence_tier` is `C`, `attributed_flag` is `0`, and **no ledger row keys any
Copper River identifier to an Eyak hub** — so a rebuild of
`prime_contracts.csv` reverts all of it. Six rows currently name one entity in
`canonical_name` and a different one in `tribe_id`.

**Why 1079 did not just finish it.** Writing a $1.5B attribution onto another
workstream's prose, with no ledger row behind it, is precisely the defect this
pass was chartered to remove. The removal from the wrong hubs is done and
proven; the destination needs a ruling that lands in the ledger.

**Consequence of each answer.** *Rule it and write the ledger rows* — the
Native Village of Eyak gains $1.5B, it survives a rebuild, and Cedar's largest
single correct attribution of the night is real rather than cosmetic. *Leave
it* — the rows stay honestly unattributed, which is a defensible state, but the
table will keep carrying `canonical_name = Native Village of Eyak` on rows with
no `tribe_id`, which is not.
<!-- END QM-QUARANTINE -->

---

## PR29-2. Seven rows in `gaming_facilities.csv` say there is no facility — and the "734" dedupe is not ready to apply

*Appended 2026-09-02 by workstream PR29-LOOP. Evidence: `docs/CODEX_REVIEW_LOG.md`, PR #29 round 4.*

### Decision A — remove or relabel the seven placeholder rows?

`gaming_facilities.csv` ships 787 rows. **Seven have `facility_name = "No casino"`:**

| facility_id | nation | state |
|---|---|---|
| `VP-0242` | Havasupai | AZ |
| `VP-0243` | Hopi | AZ |
| `VP-0102` | Quartz Valley | CA |
| `VP-0254` | Zuni | NM |
| `VP-0336` | Pueblo of Zia | NM |
| `VP-0337` | Pueblo of Cochiti | NM |
| `VP-0338` | Pueblo of Picuris | NM |

They record that a nation does **not** operate a casino. That is a real and
useful fact — Cedar deliberately distinguishes "attempted, none found" from
"untouched" — but it is being carried in the **facility** table, where every
row is otherwise a facility. **787 rows; 771 facility rows once all 16 `no casino` names are removed; 714
distinct properties once the same-tribe duplicate groups collapse** *(**GAMING-DENOMINATOR-2026-09-02:** `gaming_facilities.csv` holds **787 ROWS, not 787 facilities** — 16 rows' NAMES say no casino (7 exactly, 9 like `Grand Canyon West - no casino`) and 57 extra rows sit across the same-tribe duplicate groups, so **771 facility rows and 714 distinct properties**. Five denominators circulated on 2026-09-02 — 787, 780, 734, 727, 714 — and only the last is the property count. Authority: `code/846_session_audit.py::_denom`; derive it with `py -3 code/1116_ruling_propagation_2026_09_02.py derive`.)*, and every "of 787"
denominator in the product README and in two of Codex's own findings is
inflated by seven.

Three options, in ascending order of work:

1. **Relabel in place** — add `is_facility = N` (or reuse an existing status
   column) so a consumer can filter. Cheapest, keeps the negative evidence,
   and every downstream count has to learn the filter.
2. **Move them** to a `gaming_absence_observations` table. Cleanest grain, and
   the negative evidence keeps a home; costs a new shipped table.
3. **Delete** — loses a genuine, deliberately collected fact. Not recommended.

**This is an owner call because it changes a published denominator**, and
because option 2 adds a table to a collection that already carries 54.

### Decision B — apply the 56-group dedupe, and on what terms?

`review/gaming_facility_duplicate_candidates_2026-09-02.csv` proposes 56
groups. **Collapsing the 52 marked `LIKELY_SAME_PROPERTY` gives exactly 734**,
which is the figure now circulating as the true facility count. It should not
be adopted as-is:

- **All 56 carry `verdict_needed`** — nothing has been adjudicated. The live
  table has `duplicate_of_facility_id` on **10** rows, not 59.
- **Four are cross-tribe** and the file flags them `DIFFERENT_TRIBES_CHECK_BOTH`:
  `7 Clans First Council` (Otoe-Missouria + Ponca), `Stables` (Miami Tribe +
  Modoc Nation), and the two `NO` groups. **`Stables Casino` is a joint
  operation, not a duplicate** — collapsing it would erase one nation's
  interest in a property, which is the exact defect Codex raised from the
  other direction in round 2 finding 5.
- **Two of the 56 are a normalisation artefact** — the grouper reduced
  `No casino` to the token `NO` and grouped Havasupai with Hopi, and four
  Pueblos with each other. Those two groups are Decision A, not duplicates.

So the honest disposition is **52 candidates to review, 4 to refuse, and a
denominator question underneath both**. If the 52 are confirmed the count
becomes 734 of which 727 are facilities; until they are, **787 is what ships**
and the product README says so.

### What is already in place

Nothing is blocked by this. The product README states 787 as the shipped row
count, names 780 as the facility count, and records 734 as a proposal with its
exceptions rather than adopting it. No figure in the product asserts a dedupe
that has not happened.

---

<!-- BEGIN HARVEST-COVERAGE-1112 -->
## HC-1. A restricted publisher's TERO list was harvested anyway, and 21 rows sit in staging

**Decision:** delete or keep `data/staging/business_registry/TBD-D01_southern_ute_indian_owned_business_list.jsonl`?

`review/tribal_vendor_list_registry_2026-08-26.csv` rules Southern Ute
`EXCLUDED_TERMS_STATED_RESTRICTIVE`, quoting southernute-nsn.gov: *"under this
license you may not: modify or copy the materials; use the materials for any
commercial purpose, or for any public display."* The excluded `list_url` is
`.../2026/03/2026-Indian-Own-Business-List.pdf`.

On **2026-09-01**, `run-2026-09-01-shardd` extracted **21 rows from that exact
PDF** into `TBD-D01`, with a cached copy at `raw/TRBF-STHUTE-00_tero_b05678af.pdf`.
The rows carry named natural persons, street addresses, phones and emails.
`TBD-D01` has **no row in the vendor-list registry**, so nothing connected the
harvest back to the exclusion. Nothing has been published from it.

**Consequence.** *Purge* — move both files to `graveyard/`, register the exclusion
against `TBD-D01` as well as `TBD-055`, and the record shows Cedar caught and
reversed it. *Keep in staging* — 21 rows of a source whose publisher has told us
not to copy it stay on disk, and the next promotion pass that globs
`business_registry/TBD-*.jsonl` will pick them up, because that is exactly how
they got here.

Evidence: `docs/HARVEST_COVERAGE_AUDIT_2026-09-02.md`, final section.

## HC-2. 634 directory rows are harvested, on disk, and invisible to every coverage number

**Decision:** promote the 16 `HARVESTED_STAGING_ONLY` sources into
`data/clean/native_owned_businesses.csv` with `publishable = N`, or leave them staged?

16 of 36 `TBD-*` files in `data/staging/business_registry/` have zero rows in the
clean table — 634 rows across 15 tribes that are not currently certifying
authorities in it at all (Puyallup 88, Hoopa 136, Aquinnah 101, Pyramid Lake 73,
Sisseton-Wahpeton 45, Bad River 39, Little Traverse 35, Citizen Potawatomi 27,
Spokane 23, Kalispel 12, Chehalis 10, Shoshone-Bannock 10, Chitimacha 7, Delaware
Tribe 4, California Valley Miwok 3). `individual_business` coverage reads 58
entities harvested instead of 73 because of it.

**All 16 are `publishable = N`**, so promotion buys internal honesty and zero
shippable rows. **`TBD-C01` must be excluded** — it is a byte-equal duplicate of
the already-promoted `TBD-079` and a glob would add 337 phantom rows. **`TBD-D01`
must be excluded** pending HC-1.

**Consequence.** *Promote* — coverage stops understating what Cedar holds, and the
publish gate does the work it exists to do. *Leave staged* — every count off
`native_owned_businesses.csv` keeps understating by 634 rows and 15 nations, and
the next agent re-harvests sources already on this machine.
<!-- END HARVEST-COVERAGE-1112 -->

<!-- BEGIN SOURCE-EXPLORATION-1111 -->

## SE-1. HUD publishes a `Content-Signal`, and Cedar has no rule for that kind of term

**Appended 2026-09-02 by the `source-exploration` workstream.** Evidence:
`docs/SOURCE_EXPLORATION_2026-09-02.md` §0; raw record in
`data/staging/source_exploration_1111/probe_log.jsonl`.

`www.hud.gov/robots.txt` allows every robot and then adds, verbatim:

```
User-agent: *
Content-Signal: search=yes,ai-train=no,use=reference
Allow: /
```

above a header stating *"ANY RESTRICTIONS EXPRESSED VIA CONTENT SIGNALS ARE
EXPRESS RESERVATIONS OF RIGHTS UNDER ARTICLE 4 OF THE EUROPEAN UNION DIRECTIVE
2019/790 ON COPYRIGHT AND RELATED RIGHTS IN THE DIGITAL SINGLE MARKET."*
A separate group names `ClaudeBot` with `Disallow: /`.

`docs/PUBLICATION_POLICY.md` `TERMS-METHOD` enumerates three things a clause can
restrict — the **source**, the **content**, or the **method**. This restricts
the **use**, which is a fourth, and it is the first one Cedar has met.

**The question.** Is harmonising HUD's published per-tribe IHBG allocation
figures into `federal_funding_transactions.csv` `use=reference` (permitted) or
`ai-train` (forbidden)? Cedar's product is a harmonised dataset of published
records, not a model — which reads as reference — but nobody has ruled it.

**Consequence.** *Reference* — HUD's ONAP pages open up, including the IHBG
**formula** allocation, which is the per-tribe entitlement and much larger than
the IHBG-Competitive rounds already on disk. *Ai-train, or undecided* — HUD
joins the restricted list and 16 IHBG objects already in
`data/raw/external/federal_award_lists/` need a disposition too.

## SE-2. NHOA's own robots.txt disallows exactly the page that holds the NHO member list

**Same workstream, same date.** This is one of the two routes
`docs/KNOWN_ISSUES.md` **A3** names for the 170 Native Hawaiian Organizations
that have no dated public record.

Measured: the origin is alive. `http://www.nhoassociation.org/robots.txt`
returns 200 and says, verbatim:

```
User-agent: *
Disallow: /ajax/
Disallow: /apps/
Disallow: /sba-private-session-with-nhoa-members.html
Disallow: /nhoa-member-list.html
Disallow: /businesssummit.html
```

`/membership.html` **is** allowed. It was fetched (36,863 bytes, saved to
`data/staging/source_exploration_1111/nhoa_membership.html`) and it contains
**no member names** — only the eligibility sentence Cedar already quotes and a
contact address. Cedar's shard H used a **Wayback capture** of
`/nhoa-member-list.html`.

**The question.** Under `PUBLICATION_POLICY.md` `TERMS-METHOD`, a restriction
attaches to the host and path that state it, and a method restriction is
honoured by dropping the routes it names. Is the Internet Archive's copy of
`/nhoa-member-list.html` **a different route to the publisher's own
publication** (and therefore covered by the same refusal), or **a third
party's independent publication** (and therefore not, by the `TERMS-SCOPE`
authorship test)?

**Consequence.** *Same refusal* — the existing shard-H rows sourced from that
Wayback capture need re-examination, and the route back in is the email
address NHOA publishes on the allowed page. *Different route* — the Wayback
capture stands and can be refreshed, and A3's first named route reopens.

**Note the other half of A3 is already answered and does not need a ruling:**
"the SBA 8(a) register remains untried" is wrong.
`data/raw/external/sba_dsbs_native_entities.csv` is a DSBS extract dated
2026-04-30 holding 5,087 Native entities, 442 of them Hawaii, and
`code/01_build_entity_spine.py` already loads it. It carries no date column, so
it still cannot close A3 — but it is `ON_DISK_NOT_PROMOTED`, not
`NOT_ACQUIRED`.
<!-- END SOURCE-EXPLORATION-1111 -->

<!-- BEGIN CORROBORATION-1118-QUEUE -->
## CORR-1 — 29 nonprofits carry `NATIVE_VERIFIED_STRICT` while their own Form 990 says otherwise

*Added 2026-09-02 by `code/1118_corroboration_layer.py`. Evidence:
`data/clean/cedar_corroboration_disagreements.csv`, verdict
`OWN_990_SILENT_AND_THE_LINK_CROSSES_A_STATE_LINE`. Full account in
`docs/CORROBORATION_LAYER_2026-09-02.md`.*

**The measurement.** `np_orgs.disposition = NATIVE_VERIFIED_STRICT` is 697 rows.
293 of them have a Form 990 narrative on disk. **214 of those 293 give no
Native signal in the organisation's own words**, and 29 of the 214 ALSO have a
Cedar link that crosses a state line — two independent reasons to doubt one
row. Six of the 29, with the organisation's own filed words:

| organisation | its own 990 says | Cedar links it to |
|---|---|---|
| KANSAS HUMANE SOCIETY OF WICHITA INC | *"YOUTH EDUCATION IS A KEY BUILDING BLOCK…"* | a Wichita-named nation |
| UNITED HABESHA COMMUNITY OF WICHITA UHCW INC | *"HELP COMMUNITY IN NEED"* | *Habesha* = the Ethiopian and Eritrean diaspora |
| WAMPANOAG COUNTRY CLUB INC | *"A PRIVATE MEMBERSHIP CLUB FOUNDED IN 1924"* | Wampanoag |
| RANCHO LA LAGUNA INC | *"TO PROMOTE AND PRESERVE THE CULTURE OF CHARRERIA"* | Laguna |
| CHICKASAW CIVIC THEATRE (**AL**) | *"COMMUNITY THEATRE PRESENTATIONS EACH YEAR"* | The Chickasaw Nation (**OK**) |
| PASADENA ROSEBUD ACADEMY CHARTER SCHOOL | *"OPERATED A CHARTER SCHOOL"* | Rosebud |

**Chickasaw, Alabama is a city.** This is the place-name defect
`docs/ENTITY_MATCH_RULES.md` already governs, arriving with Cedar's *strongest*
nonprofit Native label attached.

**What is being asked.** Not "are these Native" one by one. **Does a
`NATIVE_VERIFIED_STRICT` row survive when the organisation's own filing gives
no Native signal and the link crosses a state line?**

**The consequence of each answer.**

- **It does not survive.** The 29 move to `EXCLUDED_PLACE_NAME_COINCIDENCE` (or
  to a new disposition) and the rule generalises: the 990-narrative family
  becomes a standing gate on the strict label, and the remaining 185
  same-state silent rows get re-examined next.
- **It survives.** Then `NATIVE_VERIFIED_STRICT` means *"a name matched an IRS
  BMF row"* and nothing more, and the codebook should say so — because a buyer
  reading "verified strict" will not guess it.
- **Case by case.** 29 rows, each with its filed quote already attached in the
  disagreement table; the redirect target is in
  `np_orgs.key_redirect_proposed_entity_id` where one exists.

**Why an agent did not rule this.** Silence in a mission statement is not a
refutation — the same miner scores *Tongass Tlingit Cultural Heritage
Institute* as `placename_only` and it is plainly Native. The state conflict is
what makes these 29 different from the other 185, and whether two weak signals
compose into a refusal is a ruling, not a computation.

**Nothing was changed.** `np_orgs.csv` was not edited.

## CORR-2 — does a trade journal vote?

*Same source. One line, and it moves the project total by about 30.*

`third_party_press` is an eighth evidence family added by this layer because
the mandate's seven had nowhere honest to put a `Trade press` citation. It
currently **votes**: a reporter is an independent observer. **30 deals reach
two independent families only because of it** (`entity_self_published` +
`third_party_press`).

The argument against: a trade journal reprinting a press release verbatim is
not observing anything, and R-A only catches that when both citations resolve
to the same URL — which they do not when a wire service re-hosts.

**If it does not vote, the project total falls from 320 to about 290.** No data
changes either way; it is one flag in `FAMILIES`.
<!-- END CORROBORATION-1118-QUEUE -->

<!-- BEGIN DEFECT-SWEEP-1115-QUEUE -->
## DS-1 — one Cedar id is carrying two different nations. Which one owns these 21 rows?

*From the retroactive defect sweep, `code/1115_defect_class_retro_sweep.py`
class C6. Full context: `docs/KNOWN_ISSUES.md` → `DEFECT-SWEEP-1115`.
**$101,976.57 and a sovereign misattribution.** Nothing was changed.*

**The decision, in one line:** do the 21 `prime_contracts.csv` rows below
belong to the **Winnebago Tribe of Nebraska** or to the **Ho-Chunk Nation of
Wisconsin**?

**Why it is a question at all.** `cedar_uid = CE-001C8-GH` appears in
`prime_contracts.csv` against **two different `tribe_id` values**:

| `tribe_id` | rows | what the rows are named |
|---|---:|---|
| `TRBF-WNNBGO-00` (Winnebago Tribe of Nebraska) | 17,259 | ALLNATIVE SOLUTIONS, FLATWATER SOLUTIONS, HCI MANAGEMENT SERVICES, HO-CHUNK SHARED SERVICES / BUILDERS |
| `TRBF-HOCHNK-00` (Ho-Chunk Nation of Wisconsin) | **21** | HO CHUNK INC (15) · HO-CHUNK CONSTRUCTION MANAGEMENT SERVICES COMPANY (6) |

The `canonical_name` on **all 17,280** of those rows is **`Winnebago`**. So
the display column already says Winnebago while the keying column says
Wisconsin on 21 of them. A consumer reading `canonical_name` and a consumer
joining on `tribe_id` get different nations from the same row.

**The two UEIs in dispute, with the expected answer stated so a check can
refute it** (owner's protocol: `cage.dla.mil`, last hop tribe-side):

| UEI | CAGE | name as recorded | rows | $ | currently on | expected |
|---|---|---|---:|---:|---|---|
| `S4LTC7CL8RW7` | **8APB4** | HO-CHUNK CONSTRUCTION MANAGEMENT SERVICES COMPANY | 6 | $100,758 | Wisconsin | **Winnebago NE** — the `…COMPANY` suffix is the Ho-Chunk Inc. house style, shared with HO-CHUNK SHARED SERVICES COMPANY (`JSCHHWMLJHA5`, CAGE 78WS1) and HO-CHUNK BUILDERS COMPANY (`WDZPLVXWVLJ3`), both already on Winnebago |
| `DMA6EKCMAPB7` | *(none recorded)* | HO CHUNK INC | 15 | $1,219 | Wisconsin | **Winnebago NE** — *Ho-Chunk, Inc.* is the Winnebago Tribe of Nebraska's economic-development corporation, Winnebago NE. Note `CKLKWJSYK9T5` "HO-CHUNK, INC." is already on Winnebago, so this may be a **second UEI for the same firm** rather than a second firm |

**The undisputed control, which is what makes the two above suspicious:**
`E14CPCHZGAC3` — "HO-CHUNK NATION OF WISCONSIN" / "Ho Chunk Nation", 17 rows,
$291,080. That one is on `TRBF-HOCHNK-00` and is plainly right. After a
ruling, Wisconsin should hold **17 rows and $291,080**, not 38 and $393,057.

**Why an agent did not rule it.** Two federally recognised nations share the
endonym *Ho-Chunk*. A name test cannot separate them — it is precisely the
class-4 trap ("one token of a multi-token hub name is not a name"). And the
attribution on these rows is the START_HERE trap #1 shape:
`attribution_method = cage_exact` (an exact identifier, so it reads as tier A)
sitting beside `identifier_ruling_method = need_v6`, **the 6.5%-accurate
method that never publishes alone**. The exactness of the key says nothing
about the correctness of the link.

**What happens on each answer.**

- **Winnebago (expected).** 21 rows repoint `tribe_id` → `TRBF-WNNBGO-00`.
  Wisconsin's prime total falls $393,057 → $291,080. `CE-001C8-GH` becomes
  1:1 with a single nation and the largest C6 finding in the project closes.
- **Wisconsin.** Then `canonical_name = "Winnebago"` is wrong on those 21 rows
  and the display column is the thing to correct — and `CE-001C8-GH` is being
  used for two nations, which is a spine defect, not a row defect.
- **Split** (some each). Then `CE-001C8-GH` must be split into two ids before
  either table can be published, because no single id can be both.

**Nothing was changed.** `prime_contracts.csv` was not edited.

## DS-2 — 1,066,926 prime rows say `UNKNOWN` where an owner should be. Blank them?

*Class C14. `$264,459,736,746`. This is a policy call, not a bug fix.*

`prime_contracts.owner_as_of_transaction_cedar_uid` holds the literal string
**`UNKNOWN`** on **1,066,926 of 1,217,768 rows (87.6%)**, carrying
**$264.5B** of `total_obligations`. `518`'s C4 check already learned this
lesson on 47,877 rows — *"a populated cell is not a resolved identity"* — and
the true scale is **22 times** what was measured then.

The consequence is not hypothetical: any coverage figure computed as
*non-blank ÷ total* on this column reports **100%** ownership attachment
where the honest figure is **12.4%**.

**The decision:** does `UNKNOWN` become **blank** (so every existing non-blank
test is right by construction), or does it stay and get a **declared
companion flag** (so the distinction between *asked and not answered* and
*never asked* survives)?

- **Blank it.** Every downstream non-blank test becomes correct with no code
  change. Loses the information that the question was asked.
- **Keep it, add `owner_as_of_transaction_status`.** Nothing downstream is
  fixed until each consumer is edited, but the refusal stays visible — which
  is this project's usual preference (*"this project counts what it drops, by
  name"*).

Same question, smaller, on `fac_tribal_single_audits.auditee_uei =
`**`GSA_MIGRATION`** — 4,103 of 6,780 rows, **$62.0B** expended, in a column
that is supposed to hold a UEI and is joined on.

**Nothing was changed.** Neither table was edited.
<!-- END DEFECT-SWEEP-1115-QUEUE -->

<!-- BEGIN LADDER-1117-1122-QUEUE -->
---

## LAD-1. EL-1, QM-2 and the splink queue were ADJUDICATED, not asked. Four things still need you.

*Appended 2026-09-02 by the ladder pass. Scripts `code/1117_ladder_adjudication.py`
and `code/1122_ladder_repoints.py`; registers `review/ladder_adjudication_2026-09-02.csv`
(252 rows) and `review/ladder_repoints_2026-09-02.csv` (36 rows). Applied, with
`verify` green and `selftest` proving `verify` fires.*

**What was decided without you**, because you said to: 96 of the 252 splink-queue
UEIs keyed ($696.8M), 156 declined ($261.2M); 27 identifiers repointed and 8
withdrawn across the Eastern Shawnee family, QM-2 and EL-1. **Every write is
tier B** — rule 8 — so nothing here claims your grade.

### LAD-1a. Confirm the seven EL-1 repoints back up to tier A, or say which rung refuses them

They are listed in `docs/KNOWN_ISSUES.md` under `LADDER-1117-1122`. Until you do,
`tier_A_ruled` sits at 1,669 against a 1,676 baseline and the gate — when it runs
again — will read that as a fall.

### LAD-1b. Ohkay Owingeh: add `San Juan Pueblo` as an alias?

EL-1 already asked. Answering it stops the detector re-raising a $2.04M
false positive every quarter. **`H1ZEEZK2D6B3` was CONFIRMED where it is**, not
moved; the proposal `TRBF-SNJUAN-00` is the San Juan **Southern Paiute** Tribe of
Arizona and acting on it would have been the largest single error available in
that file.

### LAD-1c. EL-2 is answered — Laulima's two owners are SEQUENTIAL, not a JV

`beringalakaina.com` names nine companies (Ke'aki, **Laulima Government
Solutions**, **Kūpono Government Services**, Kāpili, Po'okela, Kīkaha, Pololei,
Alaka'ina Professional Services, Alaka'ina Technical Services), records that the
**Alaka'ina Foundation** — a Native Hawaiian Organization certified 2004 —
established and ran them from 2005, and states they *"were wholly acquired in
June 2026 by BSNC"*.

**Two consequences you should rule on.** (1) Kūpono's CAGE `5XMJ1` ($351.0M) is
keyed here to the **Alaka'ina Foundation**, because effectively all the money
predates June 2026 — is that right, or should the identifier follow the current
owner with `owner_as_of_transaction` carrying the history? (2) **This is a deal
Cedar can report**: a nine-company NHO family acquired by an ANC, June 2026,
visible in the contracting record.

### LAD-1d. Three firms the ladder could not settle, and what was tried

| firm | $ | rung 1 | rung 2 | rung 3/4 |
|---|---:|---|---|---|
| `Hui O Ka Koa, Llc` (Honolulu) | $64.30M | HI, matches the proposal — and the proposal rests on the word `koa` | `huiokakoa.com` does not resolve | co-located UEIs are a generic Honolulu list |
| `Friend Contractors - White Mountain Jv` (Kodiak AK) | $19.48M | **Kodiak, ~1,000 km from White Mountain**; its neighbours are a Kodiak/Alutiiq cluster | no site | — |
| `Ascg Incorporated Of New Mexico` | $16.57M | Albuquerque only | `ascg.com` does not resolve | — |
| `Sea Lion Security & Control` + `Sea Lion International` | $6.08M | both Anchorage, which discriminates nothing | — | **Cedar contradicts itself**: the register holds `Sea Lion Corporation` as a village corporation `CE-000BV-SK`, `nest_enterprises.csv` holds a `Sea Lion Corporation` under **Choggiung, Ltd.** `CE-00088-R8` |
| `Indian Walk In Center` — **settled**, listed to show the route | $33.20M | — | uicsl.org names no former name; `indianwalkincenter.org` is a parked GoDaddy page | **the UEI carries BOTH names in `prime_contracts`** |

The Sea Lion row is the only one that is Cedar's own fault. **Which record is
right?**

<!-- END LADDER-1117-1122-QUEUE -->

<!-- BEGIN CAPABILITY-1114-QUEUE -->
## CAP-1. Ely Shoshone: the record says the host refuses us. It does not, today.

*From `code/1114_capability_statement_harvest.py`, 2026-09-02. Full account:
`docs/CAPABILITY_STATEMENT_HARVEST_2026-09-02.md` §2.*

**What Cedar records.** `review/tribal_vendor_list_registry_2026-08-26.csv`
excludes `elyshoshonetribe.com` as `ROBOTS_DISALLOW`, quoting *"robots.txt
explicitly names and disallows 'ClaudeBot', 'anthropic-ai', 'GPTBot',
'Amazonbot' and others"*, with the note *"The origin explicitly refuses
ClaudeBot and anthropic-ai. Fetching the same content from an archive would
honour the letter of robots.txt and defeat its purpose. Manual research only."*
`review/1020_named_agent_robots_exposure.csv` rows 40-41 carry it forward and
shard N purged the host's bodies on it.

**What the file says, fetched 2026-09-02, one request, reproducible.** It is the
Squarespace template and it is **one group**: thirty `User-agent:` lines —
`AI2Bot`, `anthropic-ai`, `CCBot`, `ClaudeBot`, `GPTBot`, … ,
`AdsBot-Google-Mobile-Apps` — then `User-agent: *`, then a single shared rule
block of **27 path-scoped `Disallow` directives**: `/config`, `/search`,
`/account`, `/commerce/digital-download/`, `/api/`, `/static/` and 21
query-parameter patterns. **There is no `Disallow: /` in the file for any
agent.** `ClaudeBot` is bound by exactly the rules the wildcard is bound by.

**The question.** Being *named* in a `User-agent:` list is not being
*disallowed*. Does Cedar read the named-agent list as a refusal anyway?

| answer | consequence |
|---|---|
| **A — the file governs; being named is not being refused** | Ely Shoshone comes off the exclusion list, its bodies may be re-fetched, and `review/1020_named_agent_robots_exposure.csv` needs re-deriving because the same conflation may sit on other rows in it. The registry note is corrected, not deleted. |
| **B — a publisher who lists us among the AI crawlers has expressed a preference, whatever the directives say** | the exclusion stands, and the *reason* in the registry should be rewritten: it is a stated preference, not a `Disallow`. Cedar then has a rule that reads intent out of a `User-agent` line, and it should be written down as such so it is applied consistently rather than per-shard. |

**Bounded, and it matters.** The file may have changed since 2026-08-26 and
nothing on this machine can prove it did not; option A does not require the
earlier reading to have been wrong at the time. What is certain is that
`www.penobscotnation.org`, checked the same minute by the same parser, **does**
carry `Disallow: /` for `ClaudeBot` and stays refused. The two hosts are
distinguishable and Cedar currently treats them the same.

**Nothing was harvested on this reading.** Robots and the home page only.

## CAP-2. 31 self-published D-U-N-S numbers — held, or dropped?

Entities published their own D-U-N-S on their own capability statements. Ruling
item 4 makes D-U-N-S internal-only, and they are flagged `may_publish = N` in
`review/capability_statement_identifiers_1114_2026-09-02.csv`.

**Hold them as an internal matching key, or do not record a proprietary
identifier at all even when the subject published it?** Holding is the current
state. Dropping costs 31 rows and removes a D&B-derived string from the
warehouse entirely.
<!-- END CAPABILITY-1114-QUEUE -->

<!-- BEGIN FWD-CONSTRUCTION-QUEUE-2026-09-02 -->

## FWD-1. 1,943,994 FAADS rows CAN be keyed after all. Spend ~60 bulk-download jobs on it, or leave the grain refused?

**The dispute is settled and both sides were half right.** Two workstreams
disagreed about why `assistance_transaction_unique_key` sits on only **825,754
of 2,769,748 rows (29.81%)** of `faads_transactions_all_agencies.csv`. Settled
by opening every staged zip and reading its header bytes
(`code/1083_faads_zip_column_census.py`, re-run 2026-09-02T15:40Z): **83 members
over 77 objects, 0 unmeasured. 23 members are 112 columns and carry the key; 60
are 20 columns and do not, one identical header signature across all 60.** The
live table splits **60 unkeyed source objects / 17 keyed**, with nothing in
between. So no re-extract of the bytes on disk recovers anything, and
derivation is closed too — two of the key's five components are physically
absent.

**What is new is that the ceiling is not permanent.** The doc said *"there is
no full-column source for those years to re-extract from."* Its own census
disproves that, and the SERVER's own job records are the evidence — two FY2001
assistance objects from the same 2026-08-05 pull, 79 minutes apart:

| state record | `total_columns` reported by the service | key |
|---|---:|---|
| `seam/_meta.json` → `"2001"` (DOI, 19:06Z) | **112** | **PRESENT** |
| `agencies/_state.json` → `jobs.ed_fy2001` (20:25Z) | **20** | ABSENT |

Same endpoint, identical record schema, identical
`All_PrimeTransactions_2026-08-05_*.zip` naming. The only difference is the
`columns` key in the payload, and `30_funding_pre2008.COLUMNS` has since been
fixed. The state is **`NOT_ACQUIRED`, not `SOURCE_DOES_NOT_PUBLISH`.**

**The ask.** A recovery pull is 10 agencies × FY2001–2006 = **60 bulk-download
jobs** (not 54 — that figure is not reproducible from any file here), one at a
time on a host that allows one poller, at roughly an hour a job.

- **Say yes** and `faads_transactions_all_agencies.csv` can declare a primary
  key for the first time, and the 3,441 remaining byte-identical rows resolve
  the way `prime_contracts`' 80,778 did — by a restored key, not a delete.
- **Say no** and the grain stays REFUSED, which is honest and is the current
  state. Nothing is broken by saying no.

**The condition, either way, is not negotiable and is why this is your call and
not an agent's:** the merge must be **by content, never by replacement**. All
**29,594** attributions in `faads_entity_attribution.csv` are keyed to
`faads_row_id`, which is a ROW POSITION. A rebuild re-points every one of them
silently. `code/791`'s fingerprint-and-ordinal pass is the route that survives
it.

Evidence: `docs/FAADS_TRANSACTION_KEY_SETTLEMENT_2026-09-02.md` (closing
section), `docs/FAADS_ZIP_COLUMN_CENSUS.json`, `docs/methodology/funding.md` §4b.

## FWD-2. FY2022 subawards: four jobs are generating right now. Nothing needed unless they fail.

Recorded so it is not rediscovered. `fy2022_q1..q4` had **never been
submitted** — FY2022 holds **89 countable rows / $47,021,525** and is now the
only empty year in `subawards.csv`. All four were submitted 2026-09-02T16:47Z
and are generating one at a time; tokens are checkpointed, so a dead poller
loses nothing. **If they come back `failed` a third time** — the full-year
`fy2022` job has already failed twice with the opaque body *"An error
occurred."* — that is the point at which FY2022 stops being a scheduling
problem and becomes a finding about the source, and it should be written down
as one rather than re-submitted a fourth time.
<!-- END FWD-CONSTRUCTION-QUEUE-2026-09-02 -->


<!-- BEGIN PLACE-IDS-DECISIONS-1129 -->
# PLACE IDS — three decisions, ADR-030, 2026-09-02

*Built and gated: `py -3 code/1129_place_ids.py verify` (15 checks, exits 1 on
breach) and `selftest` (proves four of them fire, including on an empty
register). Nothing below blocks what shipped; each is a ruling only you can
make.*

## PL-1. Two casinos are filed to two different tribes each. Which tribe operates them?

These are the only two duplicate groups where the SAME PLACE is filed to
DIFFERENT SOVEREIGNS, so a duplicate sweep cannot settle them — merging would
decide an ownership question by way of a de-duplication.

| place | address | vintage A | vintage B |
|---|---|---|---|
| **7 Clans First Council Casino (Hotel)** | 12875 N Hwy 77, Newkirk OK 74647 | `VP-0170` -> **Ponca Tribe of Indians of Oklahoma** | `CCP-843900` -> **Otoe-Missouria** |
| **(The) Stables Casino** | 530 H St SE, Miami OK 74354 | `VP-0153` -> **Modoc Nation** | `CCP-305300` -> **Miami Tribe of Oklahoma** (the `tribe` field says *"Modoc Tribe of Oklahoma/Miami Tribe of Oklahoma"*) |

- **Answer "one operator, X"** and the pair merges into one `cedar_place_id`,
  the gaming place count falls from 717 to 716 (or 715 for both), and the
  loser's row keeps its `facility_id` as evidence.
- **Answer "jointly operated"** — which is the documented history of The
  Stables — and they stay ONE place with TWO operators, which
  `gaming_facilities.operating_entity_cedar_uids` already has a column for.
- **Say nothing** and they stay two places, which is the current state and is
  the conservative direction: no dollar is keyed on the split.

Evidence: `review/place_gaming_adjudication_2026-09-02.csv`, rows with
`rule = P0_different_operators`.

## PL-2. A casino and its hotel: one place or two?

Three groups are held apart because **Casino City Press itself minted two
distinct property ids** for them, and Cedar does not overrule a source's own
property-level distinction with a name test. They are the entire difference
between the adjudicated count (**717**) and the mechanical one gated in
`846::_denom` (**714**).

| group | the two records | our read |
|---|---|---|
| Cities of Gold, NM | `Cities of Gold Casino` (39300) / `Cities of Gold Hotel` (841600), both 10-B Cities of Gold Rd | a casino and its hotel |
| Glacier Peaks, MT | `Glacier Peaks Casino` (406800) / `Glacier Peaks Hotel` (1005500), 6 m apart | a casino and its hotel |
| Three Rivers, OR | `Three Rivers Casino` (1126400, Coos Bay **97420**) / `Three Rivers Casino Resort` (639700, Florence **97439**) | **two different casinos, 67 km apart. This one should never merge.** |

**The question is only about the first two.** If a hotel attached to a casino is
one place for Cedar's purposes, the count becomes 715 and the rule generalises
to every future casino/hotel pair. If it is two, the current state stands and
714 is simply the wrong denominator to quote.

## PL-3. Generalise `Deal_ID` into a Cedar EVENT id? (recommended: yes)

You said *"transactions or deals or events, and they need to be probably queued
per dataset"*. Events **pass the ID test**: the Bristol Bay Industrial / GHEMM
acquisition of 2022-06-15 is held twice — `ANCSA2-2022-003` from the ANCSA
portal and, independently, in EDGAR — the deals merge had to refuse 36 internal
duplicates by hand, and no external id survives the same transaction being
reported twice (an SEC accession identifies a *filing*, a PIID identifies an
*award*).

**And `Deal_ID` has the same defect `facility_id` had: it is SOURCE-SCOPED.**
1,073 rows, **15 channel prefixes** — `FA-NTI` 272, `FA-HUD` 222, `ND-202…` 154,
`NLTR-2…` 90, `FA-EDA` 51, `FA-DOE` 49, `ANCSA2` 42, `ANCSA-` 34, `ANCSA3` 24,
`SECX-2` 22, `MA2020` 14, `ACQ202` 8, `IDOBS-` 2. The prefix says which pipeline
FOUND the event, exactly as `CCP-`/`VP-` say which vintage found the casino.

- **Say yes** and `Deal_ID` stays on every row as the source key while a
  `CEDAR-EVENT-nnnnnn-CC` is minted beside it — one concept, one id, one
  append-only register, and it extends to ownership changes visible only in
  contracting that were never reported as a deal. It needs the same
  one-at-a-time adjudication the 58 gaming groups needed, which is why it was
  not done unasked.
- **Say no** and deals keep 15 channel-scoped keys, and the same event found in
  two channels stays two rows until someone notices.

**It was deliberately NOT minted tonight**: the mandate was one id and only one,
and *"I don't want a billion IDs"* is best honoured by proposing the
generalisation rather than shipping a second id in the same pass.
<!-- END PLACE-IDS-DECISIONS-1129 -->


<!-- BEGIN NP-WEBSITE-1125 -->
# The nonprofit websites answered, and 26 rows now need one ruling — 2026-09-02

*Appended by `code/1125_np_website_native_check.py`. Full evidence:
**`docs/NP_WEBSITE_NATIVE_CHECK_2026-09-02.md`**; the row-level file is
`review/np_website_native_check_2026-09-02.csv`, 697 rows.
`1125 verify` exits 0, `1125 selftest` fires 7 of 7.*

You asked us to check the nonprofits' own websites. We did — 697
`NATIVE_VERIFIED_STRICT` organisations, every URL taken from a field the filer
typed on its own IRS return, **no domain guessed**, 167 pages actually read.

## The one decision

**26 organisations whose own Form 990 says nothing Native, and whose own
website describes a NON-Native community, place or institution type for
itself.** Cedar currently labels every one of them
`disposition = NATIVE_VERIFIED_STRICT` — its strongest nonprofit Native label —
on the strength of a name match over an IRS BMF row. Four of the 26 also cross
a state line and are the sharpest cases:

| organisation | state | its own website says |
|---|---|---|
| KANSAS HUMANE SOCIETY OF WICHITA INC | KS | *"HILLSIDE, WICHITA, KANSAS 67219 … WELCOME TO THE KANSAS HUMANE SOCIETY!"* |
| WAMPANOAG COUNTRY CLUB INC | CT | *"Premier Private Club in CT — Wampanoag Country Club … Dining Reservations Pool Paddle Tennis Golf"* |
| CHICKASAW CIVIC THEATRE | AL | *"…the theater relocated to a former scout hut… between Paul Devine Park and Chickasaw E[lementary]"* |
| CALIFORNIA CLUB OF LAGUNA WOODS VILLAGE | CA | *"Featuring dazzling costume changes, stellar live vocals… 28 Classic Hits"* |

**Say DEMOTE** and those 26 move to a non-Native disposition with the quote and
the saved page as the basis. The place-name families become visible as families
— *Chickasaw* is a city in Alabama and a county in Iowa and Mississippi,
*Mohegan* is a hamlet in Westchester County NY (five volunteer-fire and colony
associations sit in this population), *Rosebud* is a town in four states,
*Laguna* is in California, and `UNITED HABESHA COMMUNITY OF WICHITA` names the
Ethiopian and Eritrean diaspora.

**Say HOLD** and they keep Cedar's strongest Native label while two independent
readings of their own words — a federal filing and a public website — both
decline to support it.

**Nothing was changed either way.** `np_orgs.csv` was not opened for writing.

## Three things worth knowing before you rule

**1. Silence is not refutation, and this pass refuses to let it read as one.**
47 more of the 214 were read in full and simply say nothing Native. They are
`CHECKED_NO_SIGNAL`, kept strictly apart from the 26, and they are **not** part
of this proposal. The counter-example is on the record: **UTAH NAVAJO HEALTH
SYSTEM** also scores `CHECKED_NO_SIGNAL` and is plainly Native — the instrument
scored the page, not the organisation.

**2. A land acknowledgement is not a self-description.** Two organisations name
a nation in order to say they are *not* it (*"one small step toward true
allyship"*; *"our Indigenous neighbours, the Lummi Nation"*). The first
classifier scored both as Native self-description. They now have their own
verdict and are excluded from every Native count here.

**3. The website is a new observer of the IRS side, but it is NOT a second
observer of the 990.** Eleven organisations' own sites say they are Native —
the first eleven `org_self_statement` assertions this dataset has ever carried,
against a `entity.website` authority that `START_HERE` records as *declared
authoritative, asserts 0 times*. Seven of the eleven also have a Native signal
in their own return. That is **one organisation saying the same thing twice, in
two regimes** — worth having, and not two evidence families. A third-party
observer for nonprofit Native status still does not exist.

## What this costs if it is left

The IRS never asserts that an organisation is Native, so **every one of the 697
rests on Cedar's own inference and nothing else** unless a second reading is
admitted. That is the measurement `docs/CORROBORATION_LAYER_2026-09-02.md` P4
made, and this pass is the first thing to move it.
<!-- END NP-WEBSITE-1125 -->

---

<!-- BEGIN OWNER-V6-NEST-2026-09-02 -->
# Your own enterprise dataset, reconciled against NEST — four decisions

*Added 2026-09-02 by `code/1130_nest_owner_v6_reconcile.py`. Evidence is in
`data/staging/nest_owner_v6/`. Nothing was appended to NEST and no id was
minted; these four answers decide what happens next.*

**The headline, so the decisions have a size.** Your
`native_entity_enterprise_dataset_v6_geocoded.csv` (18,110 rows, 658 parents)
was put through NEST's own `(owner hub, normalised name)` clustering:
**440 enterprises we already hold, 4,786 net new, and 1,170 NEST holds that
your file does not** — 614 of those in no form at all, and 592 of the 614 are
firms that appear in no federal contracting record, which is exactly what the
scraping was for.

---

## OV6-1. Which of your five files is the record? (recommendation: v6, and
## retire v5)

**v6, and it is not close.** `hq_state` in v1, v2, v3 and v5 is **not a
state** — it holds the row's own 12-character UEI on 12,127 / 12,127 / 12,127
/ 11,390 rows respectively. v6 is the only file where that column is clean
(0), and it also adds `hq_zip`, `hq_address_line`, and lifts `hq_city` from
5,178 to 15,556. v5 and v6 hold the *same* 18,110 rows and differ in only
four columns; v6 is the repair of them.

**But v6 is not a superset of v3.** 160 rows / 158 firms present in v3
survive normalisation and are absent from v6 — all 160 carry a UEI
(`BOWHEAD PROTECTION & SECURITY SERVICES LLC`, `AKIMA FACILITIES MANAGEMENT,
LLC`, `UMIAQ DESIGN, LLC`, `CHEROKEE SERVICES GROUP LLC`, …).

> **The question:** do we carry those 160 forward, or did you drop them on
> purpose? List: `data/staging/nest_owner_v6/v3_recovery_candidates.csv`.
> **If you say carry**, they join the ingest in OV6-2. **If you say dropped
> on purpose**, we record the reason so nobody re-adds them.

---

## OV6-2. 4,786 net-new enterprises: ingest at what relation? (recommendation:
## `affiliation`, upgraded only where a source states ownership)

They arrive with real identifier coverage — 3,576 UEIs, 775 CAGEs, 775 8(a)
certifications, 2,632 with a city and state, 1,113 nonprofits. But your file
records **no relationship word**, so nothing in it says whether a row is
ownership (`structures`) or affiliation (`ties`). Their evidence families
are 2,338 `cedar_inference` (a resolver output), 1,855 `federal_registry`,
474 `human_ruling` (your hand file), 257 the entity's own website.

`1130` refuses to propose a relation for any of them — an affiliation
recorded as ownership is the defect NEST is most exposed to.

> **The question:** ingest all 4,786 as `affiliation` and let a later pass
> upgrade the ones a source actually supports? Or ingest only the 721 whose
> evidence family is `human_ruling` or `entity_self_published` and hold the
> rest?

---

## OV6-3. 212 of your rows hub an ANC subsidiary on a village GOVERNMENT
## (recommendation: correct your file, ours is right)

`Alutiiq LLC` and *Afognak Diversified Services* sit under
`AKNF-AFGNAK-00-KONIAG` — the Native **Village** of Afognak — rather than the
Afognak Native **Corporation**. Same at Aleknagik, Agdaagux and Arctic
Village: 212 rows in all. `ANCSA_OWNERSHIP_RULING` rule 2 says a village
government cannot own an ANCSA corporation, and Cedar's own
`village_government_owns_an_anc()` returns `False` unconditionally. NEST is on
the corporation side on all 212.

> **The question:** confirm the ruling applies, and we hand you the list to
> repoint in your file rather than us silently overriding it. Column
> `hub_disagreement_class` in
> `data/staging/nest_owner_v6/enterprise_reconciliation.csv`.

---

## OV6-4. Eight of your parents do not resolve. Six are spine gaps.
## (recommendation: mint the six)

650 of your 658 `tribe_id` values crosswalked (632 are already live Cedar
handles). The eight that did not:

* **Six intertribal organisations Cedar does not hold at all** — NAFOA, NAJA,
  the Indian Land Tenure Foundation, First Nations Development Institute, the
  Inter-Tribal Council of the Five Civilized Tribes, and IHS Tribal
  Self-Governance. These are register additions, not matching failures.
* **`TRBF-CSAKT-00` Confederated Salish & Kootenai** — held as ambiguous
  because Cedar's canonical name is the truncated `Confederated Salish` and
  `Kootenai` is a separate tribe. NEST's `held_rows.csv` already holds this
  same entity for the same reason, so it is one ruling that clears two places.
* **`NHO-MANUKAI-00` Manu Kai LLC** — also already in `held_rows.csv`; not in
  the spine.

> **The question:** mint the six intertribal organisations, and rule
> `Confederated Salish & Kootenai` onto `TRBF-CSKTFR-00` (12 rows here, plus
> the NEST holds).

---

## And one thing that is NOT a decision, only a finding you should see

**Cedar's `data/spine/cedar_identifier_ledger.csv` is largely your own file
already.** 13,191 of its 19,232 rows came from
`master_tribal_entity_registry.csv`, and 13,070 of those UEIs are in v6. So
your identifiers mostly **cannot** corroborate ours — they are ours. Of 696
identifier pairs, only **33** are a genuine second observer.

The proof: the ledger's `state` column holds the row's own identifier on
**12,127** rows — the identical count to `hq_state` in your v1/v2/v3. The
column-shift defect travelled into Cedar's spine with the file. Only 3,481 of
16,487 `state` values are a real two-letter code. Flagged, not edited — it
needs an owner.

**3,306 of your UEIs are in no Cedar table at all.** That is the real
identifier value in your file, and it is the ingest in OV6-2.
<!-- END OWNER-V6-NEST-2026-09-02 -->

---

<!-- BEGIN LEDGER-STATE-1134-2026-09-02 -->
## LS-1. Your registry builder writes the UEI into the state column. One line, still live.

*Appended 2026-09-02 by `code/1134_repair_ledger_state_uei_contamination.py`.
Cedar's side is REPAIRED and does not wait on you. This item is about the file
on your machine, which is still producing the defect.*

### What was wrong, and it is not what the previous block above says

The block `OWNER-V6-NEST-2026-09-02` (immediately above) calls this a **column
shift**. **It is not. The shift width is zero.** Measured three ways:

| evidence | result |
|---|---|
| `native_entity_enterprise_dataset_v3.csv` vs `v6`, 11,392 rows matched 1:1, all 26 columns | only `hq_state` (11,392) differs, plus `hq_city` / `hq_zip` which are v3-**blank** and were filled later by your geocoder. Every other column byte-identical |
| `master_tribal_entity_registry.csv`, 13,191 rows x 12 columns | exactly **one** column ever equals the row's own UEI: `physical_state`, 12,127 times. Both neighbours 100% populated and correctly typed |
| the code | a named-column fallback, quoted below |

A shift of width N leaves N columns of debris on one side and a hole on the
other. There is neither. **One cell is overwritten; nothing is displaced.**

### The line

`dissertation/data/tribal_federal_spending/sam_extracts/build_master_entity_registry.py`, **line 126**:

```python
physical_state=("recipient_location_state_code", "first")
    if "recipient_location_state_code" in prime.columns
    else ("awardee_uei", "first")
```

`master prime file.dta` has no `recipient_location_state_code`, so the `else`
branch fired and aggregated **the UEI** into `physical_state` for every UEI in
master prime — 12,127 of 13,191 rows. The other 1,064 came in by the
hand-matched path, never went through that groupby, and carry a real state
(134) or a blank (929).

**This is the part worth your attention.** A column shift is a parser bug: you
fix the reader once. A fallback that silently substitutes a *different, real*
column cannot fail loudly — it produces a full column of plausible-looking
values — and the same line will do it again for whatever column gets renamed
upstream next. Every consumer of `physical_state` in that repo has been reading
UEIs for 92% of rows since 2026-05-01.

**Your attribution logic is NOT affected.** `cluster_v3_parent_brand.py` line
237 takes state from `recipient_state_code` directly, and its `geo_ok` gate was
live throughout. The damage is confined to the registry file and the NEED
enterprise datasets v1/v2/v3 built from it. **v5 partially and v6 fully repair
it** (v6: 0 contaminated rows), which is why Cedar could recover.

> **The question, and it is yours because it is your repo:** fix line 126 to
> RAISE when `recipient_location_state_code` is absent, rather than substitute.
> Cedar cannot do this for you and Cedar's guard does not protect your own
> analyses.

### Cedar's side — done, not waiting

Repaired from **your v6**, keyed on `enterprise_uei`, writing a state only
where v6 gives exactly one two-letter value and leaving it **BLANK** otherwise.
Nothing guessed:

| table | contaminated | recovered from v6 | left BLANK |
|---|---:|---:|---:|
| `data/spine/cedar_identifier_ledger.csv` | 12,127 | **11,943** | **184** |
| `data/clean/cedar_publishable_identifiers.csv` | 699 | **697** | **2** |
| `data/clean/cedar_identifier_ledger_tiered.csv` | 0 | — | — |
| `data/clean/cedar_identifier_ledger_final.csv` | 0 | — | — |

Plus 828 full state names normalised (`Oklahoma` -> `OK`) and **24,121 blank
`state` cells filled** from v6 across the clean ledgers — `71_fix_known_defects.py`
had *blanked* the contaminated cells rather than recovering them, and v6 knew
the answer for 12,019 / 12,026 of them.

**48 multi-state strings (`Alabama; Texas`) and 3 junk values (`BRUNEI &
MUARA`, `-`) were LEFT EXACTLY AS THEY ARE.** Blanking them is a deletion of
evidence with no recovery behind it. They are flagged, not edited.

### The $8.21B hypothesis was tested and is FALSE

It was put to this pass that the 15,878 `ledger_uei_state_disagreement_withheld`
rows in `federal_funding_transactions.csv` — **$8,210,723,480.00** across 120
proposed entities — might have been withheld against a corrupted state, making
the withholdings spurious and the money wrongly unattributed.

**Measured: 0 of 15,878 rows. $0.00 of $8.21B.**

`code/115_pull_assistance_archive.py` line 892 builds its comparison state from
`cedar_entity_spine.csv`, keyed on `tribe_id`. It has never read the identifier
ledger's `state` column. The spine's own `state` is clean — 1,492 two-letter
codes, 63 blanks, **zero UEIs** across 1,555 rows — and a blank yields
`agree = "unknown"`, which cannot withhold. All 120 proposed entities carry a
real two-letter spine state.

98 of those 120 entities *do* have contaminated ledger rows, which is exactly
why the coincidence reads as causal. It is not. **The withholdings stand and
nothing is re-attributed.** Santa Clara County Housing Authority (CA) is still
not Pueblo of Santa Clara (NM).

**No decision is required on this.** It is recorded here so it is not
re-opened as an $8.2B question a fourth time.
<!-- END LEDGER-STATE-1134-2026-09-02 -->

---

<!-- BEGIN GAMING-PLACE-RULINGS-1141-2026-09-02 -->
# GP-1 and GP-2 — two gaming properties, each filed to two nations

*Appended 2026-09-02 by workstream `GAMING-THIRTEENTH-1141`. Full evidence per
group: `review/place_gaming_hold_open_disposition_2026-09-02.csv`. Write-up:
`docs/GAMING_THIRTEENTH_DATASET_2026-09-02.md` §3.*

`review/place_gaming_adjudication_2026-09-02.csv` held **five** groups open.
**Three are now settled as genuinely separate places and need nothing from
you** — Three Rivers (Coos Bay and Florence, 67 km apart), Glacier Peaks and
Cities of Gold (a casino and its hotel, which the standing rule already treats
as two places). None of the three moves any count.

These two do need you, because each decides which sovereign a property belongs
to, and **either answer moves the settled denominator of 717.**

---

## GP-1 — THE STABLES (Miami, Oklahoma). One property, two operators, both real.

**The facts are settled.** `VP-0153` and `CCP-305300` are the same casino at
530 H Street SE, Miami OK 74354 — same address, coordinates 1.1 km apart. It is
a genuine **joint operation of the Miami Tribe of Oklahoma and the Modoc
Nation**, and Casino City's own row says so in one string:
`"Modoc Tribe of Oklahoma/Miami Tribe of Oklahoma"`, while keying it to
`TRBF-MIAMIT-00`. The other vintage keys the same address to `TRBF-MODOCN-00`.

**The decision.** A `cedar_place_id` is a SUB-HUB of the entity that OPERATES
the place, and this place has two operators.

| answer | consequence |
|---|---|
| **merge, hang it from both** | 717 → **716**. `gaming_facilities` already supports it: one row today carries `n_operating_entities = 2` with `operating_entity_basis = joint_operation_declared_in_source`. The place-id model gains its first two-parent place |
| **merge, hang it from one** | 717 → **716**, and you name which nation |
| **keep two** | 717 stands; the file keeps two ids for one building, and the review row stays open for ever |

---

## GP-2 — 7 CLANS FIRST COUNCIL (Newkirk, Oklahoma). One vintage names the wrong nation.

**One property**: `VP-0170` and `CCP-843900`, both `7 Clans First Council
Casino`, both at **12875 N Highway 77, Newkirk OK 74647**. `CCP-843900` files
it to the **Otoe-Missouria Tribe of Oklahoma**; `VP-0170` files it to the
**Ponca Tribe of Indians of Oklahoma**.

**The evidence points one way.**

1. The Otoe-Missouria Tribe's **own casino listing** —
   `https://www.omtribe.org/who-we-are/enterprises/gaming/casino-listing/` —
   names *"7 Clans First Council Casino, 12875 North Highway 77 Newkirk, OK
   74647"* as its property. The operator publishing its own address.
2. The **NIGC gaming location map** lists `7 Clans First Council Casino` at
   `12875 North Highway 77, Newkirk OK 74647`. Cedar already carries that link
   at **tier A** in `gaming_nigc_roster_link.csv`, `match_basis
   exact_name_state`.
3. Cedar's **other five `7 Clans` rows are all Otoe-Missouria** (Chilocco, Red
   Rock, Paradise, Perry, Gasino Chilocco).
4. The likely origin of the error: **two casinos sit on Highway 77 in Newkirk**
   — First Council at 12875 (Otoe-Missouria) and Native Lights at 12375
   (Tonkawa) — and the Ponca Tribe's own gaming is in Ponca City.

**Why it was not just applied.** The wrong `tribe_id` has already PROPAGATED.
`gaming_property_federal_traces.csv` attaches the **Ponca** tribal-state
compact `CMP-OK-ponca-tribe-of-indians-of-oklahoma-20020208` to this property,
and `nigc_region_assignments.csv` carries two rows keyed to `TRBF-PNCAOK-00`.
Repointing the display columns and leaving the derived traces is the Copper
River defect exactly. No dollars key off `VP-0170` — it appears in no revenue
or money table — so this is a clean repoint, but it is still a repoint between
two sovereigns.

| answer | consequence |
|---|---|
| **repoint `VP-0170` to `TRBF-OTOMSA-00`** | 6 rows across 5 tables change nation; the Ponca compact trace must be re-derived; the group then merges under rule P2 and 717 → **716** |
| **leave it** | Cedar publishes a property asserting the Ponca Tribe operates a casino the Otoe-Missouria Tribe says is theirs |
<!-- END GAMING-PLACE-RULINGS-1141-2026-09-02 -->
