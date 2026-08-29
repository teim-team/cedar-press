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
