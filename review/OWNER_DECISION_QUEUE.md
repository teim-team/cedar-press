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

1. **`prime_contracts_entity_year.csv` — ANSWER FIRST.** `(tribe_id,
   fiscal_year)` collides on 1,751 of 8,464 rows; uniqueness needs
   `canonical_name` + `confidence_tier`. **Anyone summing `obligations_usd`
   by tribe-year double-counts today.** Is the grain entity-year (then the
   table needs a rebuild that collapses variants) or deliberately
   entity × name-variant × tier × year (then the docs must shout it)?
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

## 4b. Fifteen tables with literal duplicate rows — pipeline defects, not rulings

For awareness, not decision (fixes route to the pipelines): prime_contracts
80,778 dup rows; faads_all 179,259; **cedar_ruling_ledger_consolidated 6,302
of 15,587 (40%)**; cross_dataset_ruling_map 30%; subawards 10,770; ferc
822; graph_edges 2,451; and 8 smaller. Full list in `docs/GRAIN_AUDIT.md`.

## 5. Suspect EIN links — 334 rows, from the first second-source harvest

`review/irs_ein_link_queue_2026-08-29.csv`. Six are self-filing entities
whose EIN files as a DIFFERENT organisation (IAIA → IAIA Foundation;
Chugachmiut (AK) → Lakota Language Consortium (IN)); 328 file cross-state;
7 ledger rows store the entity's name where the filer's belongs. These are
link-quality findings — batch-rule or sample-and-rule as you prefer.

## 6. Grain rulings — incoming from workstream E (superseded by §4 above)

Workstream E is testing candidate keys for the 207 shippable tables without a
declared grain. Tables where the data is ambiguous will land here as
OPEN_WITH_EVIDENCE items with collision counts attached. Expect a batch; each
should be answerable from its evidence line.
(`federal_funding_transactions.csv` is already one: union of two pulls, no
ruling yet on key uniqueness across the seam.)

## 7. Standing items from earlier sessions (unchanged)

- `gaming_property_locations` publishable filter (741 rows `publishable = N`)
- `consultation_agency_coverage` split decision
- `wa_machine_transfers` empty-or-real decision
- B&B git-history decision on the PUBLIC repo (accept vs filter-repo)

---

## 8. Correctness pass 2026-08-29 — three items an agent could not close

*Appended by the correctness agent. §4b's "fifteen tables with literal
duplicate rows" is partly ANSWERED below and the answer changes what it is
asking for.*

### 8a. `ship_dist_rows` cannot return to its floor, and the allowance is
### single-use by construction

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
