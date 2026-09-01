# Owner decision queue — everything waiting on Elijah, one page

*Consolidated 2026-08-30 by the integrator. Each item states the decision, the
evidence already gathered, and what happens on each answer — so a ruling takes
a minute, not an investigation. Newest evidence first. Items are removed when
ruled; new agent proposals should be APPENDED here as well as to their inbox
file.*

---

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
