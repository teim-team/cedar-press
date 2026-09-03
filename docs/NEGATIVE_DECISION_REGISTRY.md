# The negative-decision registry

*Built 2026-09-02 by `code/1163_negative_decision_registry.py`. Internal
infrastructure. It is **not** one of the twelve customer datasets and must never
appear on a shelf — `cedar_publication.STOREFRONT_SHELVES` / `BUILD_SHELVES`
define what does, and invariant I10 fails if this ever shows up there.*

---

## The claim it refuses to make

> *"I would not create a table that says `is_native = false`. That claim is too
> broad and will create its own serious errors. Build an internal
> negative-decision registry that records precisely what Cedar ruled out."*
> — the owner, 2026-09-02

Every row rules out **one of four things**, and never an identity:

| what is denied | predicate | example on disk |
|---|---|---|
| a **relationship** | `owned_by`, `controlled_by` | Goldbelt Hawk is not owned by Tlingit & Haida |
| an **identity match** | `same_entity_as` | Bristol Bay Area Health Corp is not Bristol Bay Native Corp |
| a **classification** | `native_ownership_status` — and only ever `INSUFFICIENT_EVIDENCE` | the Lawelawe / Ho'omaka parent hypothesis, tested and not established |
| **dataset eligibility** | `eligible_for_collection` | 123 UEIs outside the tribally-owned collection |

Read the third column again. Goldbelt is an ANCSA corporation; the denial is
about the *edge*. UTTC is a tribal college; the denial is about the *owner*. Of
the 123 eligibility exclusions, **31 are `individually_native_owned` and 26 are
`nonprofit_not_tribally_owned`** — every one of the 57 is Native, and every one
is out of scope precisely because the collection is about *tribal* ownership. A
table that read `is_native = false` would have swallowed all 57.

---

## One source of truth, not a parallel dataset

> *"Your link layer already has proposed, contested, denied, unresolved and
> verified states. I would strengthen that layer with structured denial reasons,
> temporal scope, evidence, supersession and dataset-eligibility predicates,
> then generate `cedar_negative_constraints` as a derived view."*

**What the link layer already carried**, measured by
`py -3 code/1163_negative_decision_registry.py report`:

`data/spine/cedar_source_record_links.csv`, 585 rows —
`link_status`: `proposed` 570 · `contested` 7 · `denied` 5 · `unresolved` 2 ·
`verified` 1; `polarity`: `affirm` 580 / `deny` 5; and it already has
`supersedes_link_id`.

**What it lacked, and what the negative half needs:** `reason_code`,
`valid_from`, `valid_to`, `as_of_date`, `evidence_strength`, `dataset_scope`,
`recheck_after`, and any hard/soft distinction. Its `status_reason` is free
prose. And it covers exactly one dataset — `source_dataset` is
`fr_recognized_entities` on all 585 rows.

Everything else Cedar had ruled out lived in whatever column the pass that made
it happened to invent — nine shapes, no shared vocabulary, no shared temporal
model:

| shape | file | rows |
|---|---|---|
| `link_status = denied` | `cedar_source_record_links.csv` | 5 |
| `key_review_disposition` / `placename_refusal_rung` | `np_orgs.csv` | 517 |
| `disposition = WITHDRAW` / `HOLD` | `review/1079_quarantine_triage_2026-09-02.csv` | 743 / 758 |
| `action = UNLINK` / `REFUTE` | `cedar_correction_register.csv` | 173 rows, 127 distinct pairs |
| `exclusion_reason` | `cedar_exclusion_rulings.csv` | 123 |
| `ruling` | `cedar_rulings.csv` | 8, of which 4 negative |
| `agrees_with_shipped = 0` | `review/temporal_asof_ownership.csv` | 411 |
| `parent_entity_type` vs `parent_entity_id` | `anc_tribal_subsidiary_lookup.csv` | 23 |
| `owner_hub_cedar_uid` | `nest_enterprises.csv` | 20 |

So:

```
data/spine/cedar_decision_events.csv        append-only.  THE source of truth.
data/spine/cedar_negative_constraints.csv   DERIVED.  Rebuilt by `build`.
data/spine/_decision_events_ledger.json     row hashes.  Enforces append-only.
review/negative_decision_review_queue.csv   DERIVED.  Everything soft or stale.
```

The nine shapes above are **seeds**, imported with the file they came from named
in `source_table` — not re-authored, and none of them deleted. `verify` I8 fails
if any `source_table` is missing from disk, so a seeded event can always be
re-derived from the file it claims.

The derived view's first data column is literally named
`THIS_FILE_IS_DERIVED` and carries the regenerate command. `verify` I9 fails if
it has drifted from the events.

---

## Schema

`cedar_decision_events.csv`, the owner's nineteen columns in the owner's order:

```
decision_id · subject_record_id · subject_entity_id · candidate_cedar_uid
predicate · decision · reason_code · reason_detail · dataset_scope
valid_from · valid_to · as_of_date · evidence_id · evidence_strength
review_status · reviewer · decided_at · supersedes_decision_id · recheck_after
```

**Three columns are appended and named as appended:** `source_table`,
`built_by_script`, `built_date`. A registry whose rows cannot be traced to the
file they were read from cannot be re-derived, and `evidence_id` holds evidence
— it is not a place to hide provenance.

`decision_id` is `NDR-` + the first 12 hex of a SHA-1 over the event's **natural
key**, which is what makes `seed` idempotent: re-running appends only ids the
file does not already carry. It is deliberately *not* a content hash — a
corrected `reason_detail` on the same pair is an edit the append-only ledger
catches, rather than a silent second row.

### `dataset_scope` may name a column

`<collection>` or `<collection>:<column>`. The qualified form exists for one
measured reason: `429_apply_asof_ownership_status.py` deliberately keeps
`cedar_uid` on a `CONTRADICTED_AS_OF` row — it is Cedar's *current* attribution
and it is correct — and publishes the historical answer in
`owner_as_of_transaction_cedar_uid`. A gate reading `cedar_uid` there would fire
on a considered design decision. So those 411 events scope to
`contractors:owner_as_of_transaction_cedar_uid`.

---

## The five rules

### 1. Hard vs soft. Only hard auto-suppresses.

> *"Otherwise the system will fossilize old research gaps and create false
> negatives."*

Hardness is **not** a property of the reason code alone. A name collision a
matcher noticed is a question; the same collision after the owner ruled on it is
an answer. `hardness()` is the single definition and I5 proves nothing escapes
it.

| class | codes | why |
|---|---|---|
| **HARD by nature** | `IDENTIFIER_CONFLICT` · `DIFFERENT_LEGAL_ENTITY` · `WRONG_ENTITY_CLASS` · `OWNERSHIP_CONTRADICTED_AS_OF` · `OWNERSHIP_ENDED` · `TRIBAL_GOVERNMENT_NOT_ENTERPRISE` · `DUPLICATE_SOURCE_RECORD` · `OUT_OF_DATASET_SCOPE` · `CERTIFICATION_EXPIRED` | a fact about the **world** that does not become false because Cedar looked harder |
| **HARD only if adjudicated** | `NAME_COLLISION` · `GEOGRAPHY_CONFLICT` | hard once `review_status = ADJUDICATED` **and** a named `reviewer`; soft otherwise |
| **NEVER hard** | `INSUFFICIENT_EVIDENCE` · `NO_QUALIFYING_CONTROL_EVIDENCE` · `NATIVE_SERVING_NOT_NATIVE_CONTROLLED` | a fact about **Cedar's research**. Fossilize it and the next matcher inherits a 2026 research gap as a 2030 fact |

Measured on the seeded registry: **734 HARD, 1,998 SOFT.**

### 2. `INSUFFICIENT_EVIDENCE` never becomes a permanent negative fact.

Forced SOFT, forced `review_status = PENDING_REVIEW`, forced `suppresses = N`,
at construction time so no seeder can forget. 759 events, 0 exceptions (I4).

### 3. No silent overwrite.

New evidence **appends** a superseding event pointing at the original through
`supersedes_decision_id`; the original is never edited. A superseding event only
takes effect once its own `review_status` is `ADJUDICATED` — a
`PROPOSED_SUPERSEDE` leaves the original standing and lands in the queue.

Append-only is enforced, not requested: `_decision_events_ledger.json` holds a
row hash per `decision_id` and I1 fails on any edit or deletion.

**The one real supersession on disk**, seeded from `cedar_rulings.csv`:
`EXCL-0116` excluded UEI `YBZGKKUPSUD4` with the reason text `ANC`; `RUL-0001`
later ruled the firm *is* attributable, to Doyon. The exclusion event is not
edited and not deleted — a superseding event bounds it with `valid_to`, so the
original reads `SUPERSEDED` and the bound reads `ACTIVE_HISTORICAL`. Both stay
on the record, which is what a history is.

### 4. Temporal.

`valid_from` / `valid_to` bound **the fact**, not the decision. This distinction
is load-bearing and the first draft got it wrong: evaluating the window against
*today* quietly stood down 403 of the 411 ownership contradictions the moment
their fiscal year ended — a gate that disarms itself with the calendar. A 2018
contradicted ownership is a permanently true statement about 2018 and must still
suppress a 2018 row published in 2030, so the window is tested against **the
published row's own date**.

- Every ownership decision carries a `recheck_after` (default `as_of` + 365d).
  I6b fails on an ownership decision that neither expires nor rechecks.
- A passed `recheck_after` does **not** un-suppress a hard constraint — evidence
  does not decay into permission. It marks it `ACTIVE_STALE` and queues it.
- **Permanent identity denials** — `same_entity_as` with
  `DIFFERENT_LEGAL_ENTITY` or `IDENTIFIER_CONFLICT` — carry no `valid_to` and no
  `recheck_after`. Two definitively different legal organisations do not become
  one later. If the original ruling was *wrong*, that is a supersession, not an
  expiry. I6 asserts it.
- I11 refuses `valid_to < valid_from`: an empty window is a constraint that can
  never fire.

Constraint states: `ACTIVE` · `ACTIVE_HISTORICAL` (in force, but only for rows
dated inside its window) · `ACTIVE_STALE` (recheck overdue, still suppressing) ·
`REVIEW_ONLY` (soft) · `SUPERSEDED`.

### 5. Release check, with a fixture that has been watched fail.

`py -3 code/1163_negative_decision_registry.py check` — no published row in
`dist/customer/` may violate an active hard constraint. Wired into
`code/846_session_audit.py` as a claim (~20s over 2.07M rows).

A collection with no probe, or a windowed constraint against a file with no date
column, is **reported as untested** rather than passing quietly.

`selftest` builds a throwaway `dist/` and asserts four things, all four passing:

| | assertion |
|---|---|
| A | a row violating a real active hard constraint → exactly **1** violation |
| B | the same row pointed at an unconstrained uid → **0**. A gate that fires on everything is not a gate |
| C | a row violating a **SOFT** constraint → **0**. Rule 1, proven |
| D | the same firm, same uid, two transaction dates: inside the window → 1, 400 days after it → 0. The acquisition case in miniature |

---

## What was seeded, from where

`py -3 code/1163_negative_decision_registry.py seed` — **2,732 events**, every
one read from disk, none invented.

| seeder | source | events | HARD | SOFT |
|---|---|---|---|---|
| `goldbelt_anc_lookup` | `data/raw/external/anc_tribal_subsidiary_lookup.csv` | 23 | 23 | 0 |
| `goldbelt_nest_published` | `data/clean/nest_enterprises.csv` | 19 | 19 | 0 |
| `uttc_united_auburn` | `data/clean/nest_enterprises.csv` | 1 | 1 | 0 |
| `np_placename_refusals` | `data/clean/np_orgs.csv` | 517 | 0 | 517 |
| `quarantine_1079_withdraw` | `review/1079_quarantine_triage_2026-09-02.csv` | 743 | 21 | 722 |
| `quarantine_1079_hold` | `review/1079_quarantine_triage_2026-09-02.csv` | 758 | 0 | 758 |
| `correction_register` | `data/clean/cedar_correction_register.csv` | 127 | 127 | 0 |
| `link_layer_denials` | `data/spine/cedar_source_record_links.csv` | 5 | 5 | 0 |
| `exclusion_rulings` | `data/spine/cedar_exclusion_rulings.csv` | 123 | 123 | 0 |
| `cedar_rulings_hand` | `data/spine/cedar_rulings.csv` | 5 | 4 | 1 |
| `temporal_contradicted_asof` | `review/temporal_asof_ownership.csv` | 411 | 411 | 0 |

Notes on the judgement calls:

- **Goldbelt is recorded at two grains** — the 23 lookup rows and the 19 rows
  the export actually publishes. `1157` fixed the lookup path today; the
  OWNERV6 path still keys 19 Goldbelt enterprises to Tlingit & Haida in
  `data/clean/nest_enterprises.csv`, and `dist/customer/nest.csv` ships them. An
  event keyed to `enterprise_id` is what the gate can test.
- **The 517 place-name refusals are SOFT**, and that is the point. `1155`
  measured its rungs on a 210-row sample; it did not rule 517 organisations one
  by one. They are already MASKed by `cedar_publication`, which is the right
  treatment. The registry records *why* without hardening it into a permanent
  negative about an organisation nobody looked at.
- **722 of the 743 `1079` withdrawals are SOFT.** They read "no rung of the
  corroboration ladder reached" — an *absence* of evidence, exactly the shape
  the owner said must not fossilize. AVCP Regional Housing Authority (UEI
  `WSPWNRKSH5N1`), attributed to Arctic Slope Regional Corporation on the single
  shared token `regional`, is one of them: the withdrawal says it is not ASRC's,
  not that it is not Native. The 21 hard ones say something positive instead —
  the awardee is a federal or state *agency*, or an FPDS-declared parent names a
  different corporation.

### Two predicates were declared and left empty, on purpose

- **`duplicate_of VERIFIED` — 0 seeds.** The obvious source was the 846
  `duplicate_status = superseded_by_primary_source` rows in
  `data/clean/subawards.csv`. A `duplicate_of` event has to *address* a record,
  and that file has **no row-unique column** — all 81 repeat.
  `subaward_source_record_id` comes closest at 89,462 distinct over 89,809 rows,
  and **346 of the 846 superseded records share their source-record id with a
  row marked `primary`**. Seeded on that key the gate reported 366 violations,
  346 of them its own bad key. The seeder was removed rather than weakened and
  the 846 events deleted before anything consumed them. When subawards carries a
  row id this is a five-line seeder.
- **`controlled_by DENIED` — 0 seeds.** Nothing on disk rules at the grain of
  control-without-ownership. The nearest candidates —
  `nonprofit_not_tribally_owned` in the exclusion rulings — are *scope*
  decisions, and calling them control findings would be the invention this file
  exists to avoid.

---

## What the gate found on the live release

```
733 active HARD constraints vs 2,074,875 published rows in 13 files: 20 violations
```

All 20 in `dist/customer/nest.csv`, and all 20 are the two cases the owner named
by hand:

- **19 × Goldbelt → Tlingit & Haida** (`CE-0006B-0K`). `1157` repaired the
  `anc_tribal_subsidiary_lookup` path (23 rows) today; the OWNERV6 path is a
  separate route into the same table and is untouched. Correct owner:
  `ANVC-GLDBLT-00` / `CE-0008Y-WE`, Goldbelt, Incorporated — which the same file
  already carries on 31 other rows.
- **1 × United Tribes Technical College → United Auburn** (`CE-00125-C6`), on
  the token `united`. UTTC already holds its own Cedar entity,
  `TCU-NTDTRB-00` / `CE-0011B-BC`.

`review/negative_constraint_violations_<date>.csv` has the rows. Repairing them
is `1072`/`1157`'s lane, not this one — this file only ever refuses.

Two results worth stating because they are the gate *not* firing: the 123
eligibility exclusions produced **0** violations against
`dist/customer/contractors.csv`, so `03_apply_exclusions_and_tier.py`'s tier-X
suppression is holding; and the 411 temporal contradictions produced 0, because
`429` masks `cedar_uid` and publishes `UNKNOWN` in the historical column exactly
as designed.

---

## Numbers in the brief that did not reproduce

| brief said | disk says | command |
|---|---|---|
| 293 nonprofit place-name refusals | **297** carry `key_review_disposition = REFUSED_PLACE_NAME_IS_THE_ADDRESS`; **517** carry a `placename_refusal_rung` (the other 220 keep `1101`'s `HELD_STATE_DISAGREES` and carry the refusal in the `placename_refusal_*` columns); **292** in `dist/customer/nonprofits.csv` per `review/1153_adjudication_states_2026-09-02.csv` | `1163 report` |
| 254 applied pairs in `cedar_correction_register.csv` | **178 rows**, 173 of them `UNLINK`/`REFUTE`, **127 distinct** `(withdrawn_key, entity_id)` pairs | `1163 report`, `1163 seed` |

`293` is a stale literal in `code/1155_np_placename_precision.py`'s docstring
(line 291) and in a comment in `code/1139_linkage_coverage.py` (line 272); the
apply pass has since moved the count to 297. Neither number is wrong about
anything except itself, but `1156_doc_claim_gate.py` should probably see them.

---

## Commands

```
py -3 code/1163_negative_decision_registry.py report    # the pre-existing layer
py -3 code/1163_negative_decision_registry.py seed      # APPEND (idempotent)
py -3 code/1163_negative_decision_registry.py build     # regenerate the view
py -3 code/1163_negative_decision_registry.py check     # the release gate
py -3 code/1163_negative_decision_registry.py selftest   # watch the gate fire
py -3 code/1163_negative_decision_registry.py verify    # 11 invariants
```

## How to add a ruling

1. Never edit `cedar_decision_events.csv`. Write a seeder that reads the file
   your ruling lives in, or append one event with a fresh `decision_id`.
2. Reversing an earlier ruling means a **new** event with
   `supersedes_decision_id` set. Set `review_status = PROPOSED_SUPERSEDE` unless
   a named person has adjudicated it; only `ADJUDICATED` retires the original.
3. `build`, then `check`, then `verify`. I9 will catch a stale view and I1 will
   catch an edited row.
4. If the ruling is a name collision or a geography conflict, it is **soft**
   until you put a person's name in `reviewer` and set `review_status =
   ADJUDICATED`. That is deliberate.
