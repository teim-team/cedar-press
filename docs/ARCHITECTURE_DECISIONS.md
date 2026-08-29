# Architecture decision log

*One entry per new primitive. Started 2026-08-30 for the post-review
implementation pass. Append only; supersede by adding a new entry that names
the one it replaces.*

## Workstream file ownership, 2026-08-30 pass

Four workstreams run in parallel. A file has ONE owner this pass. If a
workstream needs a change inside another's file, it records the request in its
handoff and the integrator stages it - no racing edits.

| workstream | owns (may edit) | must not touch |
|---|---|---|
| **A** source-record → UID | `code/514_source_records.py`, `docs/SOURCE_RECORD_LAYER.md`, its own new tables | `510`, `512`, `62`, `build.py`, `503` |
| **B** temporal + observation | `code/515_temporal.py`, `docs/TEMPORAL_MODEL.md`, its own new tables | `510`, `512`, `62`, `build.py`, `503` |
| **C** release replay | `code/516_release_manifest.py`, `code/build.py`, `docs/RELEASE_REPLAY_LOG.md` | `510`, `512`, `62`, `503` |
| **D** resolver + contracts | `code/510_assertions.py`, `code/512_build_dataset_contracts.py`, `code/62_no_regression_check.py`, `code/503_identity.py` | `build.py`, A/B/C new scripts |

Shared, read-only for everyone: `cedar_pipeline.py`, `cedar_codebook.py`,
`cedar_domain.py`. No workstream commits; the integrator commits.

---

## ADR-001 — `source_record` as a first-class node (workstream A)

**Status:** in progress. **Supersedes:** nothing.

**Context.** External review finding F1, the deepest in that review: Cedar's
assertion layer begins *after* a source row has been resolved to a
`cedar_uid`, so the source's factual claim and Cedar's entity-resolution
decision are fused. An authoritative source can therefore launder a bad match
into an authoritative Cedar fact — the Federal Register is authoritative about
its own row, never about our mapping of that row to a uid.

**Decision.** Three claims must be separately representable and separately
refutable:

```
source record R asserts   official_name = N        <- authority applies HERE
source record R asserts   recognition   = yes      <- authority applies HERE
source record R refers_to candidate uid G          <- authority NEVER applies here
```

`refers_to` carries its own evidence, method, confidence, and status
(verified / contested / denied / unresolved).

---

## ADR-002 — observation distinct from assertion (workstream B)

**Status:** in progress.

**Context.** Review finding F11: an assertion id is content-addressed over
(subject, predicate, object, source, polarity), so re-checking a source that
still says the same thing produces the *same* id. The layer must then mutate
an append-only row, keep a stale date, or duplicate an id — all three wrong.

**Decision.** A **claim** is immutable and semantic. An **observation** is an
event: (assertion_id, retrieved_at, source_snapshot, verifier, result). Recency
reads observations; the claim never changes.

---

## ADR-003 — validity time distinct from observation time (workstream B)

**Status:** in progress.

**Context.** Review finding F5: Cedar applies current truth to historical
transactions. A subsidiary sold in 2027 would mis-key its pre-sale awards.

**Decision.** Facts carry `valid_from` / `valid_to` (when the fact was true of
the world), `source_effective_date` (when the source says it took effect, if
stated), and `observed_at` (when Cedar looked). **Unknown dates are recorded as
unknown and never invented to make an interval tidy.**

---

## ADR-004 — a release must retain its inputs (workstream C)

**Status:** in progress.

**Context.** Review finding F13: "a checksum is a receipt, not a backup." Our
replay drill proved code at a commit runs; it never proved inputs could be
retrieved.

**Decision.** A release manifest names every transitive input with its content
hash AND a retained immutable location. Where an input cannot be retained, the
manifest says so explicitly and that release is marked
**not-exactly-replayable** with the blocking component named.

---

## ADR-005 — resolution is per-predicate policy, not one global order (workstream D)

**Status:** implemented 2026-08-30. **Supersedes:** the single lexicographic
rule order described in `docs/ASSERTION_LAYER.md`.

**Context.** Review finding F10. `R01 DENY_VETO` ran before `R02 AUTHORITY`,
so an equal-tier deny from a source with no authority over the predicate
removed an authoritative Federal Register affirmation before authority was
ever consulted. The reviewer's wider point is the one that matters: one
universal order cannot serve stable legal status, current leadership, mailing
addresses and ownership at once.

**Decision.** A predicate declares a **policy**; the policy owns its rule
order and its deny semantics. Written as data to
`data/spine/cedar_resolution_policies.csv` so a buyer can audit it.

```
rank_order                      this predicate's precedence over the scoring
                                dimensions (authority, human, tier, families,
                                recency)
deny_may_veto_authority         may a non-authority deny remove an
                                authoritative affirmation? The authority
                                RETRACTING ITSELF always may.
deny_may_be_older_than_affirm   may a deny that predates the affirmation it
                                names still veto it?
corroboration_horizon_days      families whose newest evidence is older than
                                this behind the freshest candidate do not
                                COUNT toward corroboration when ranking. The
                                honest full family count is still reported.
```

A deny the policy blocks is **not discarded** — it is written to the conflict
table as `R01-BLOCKED`, a live contest that wins the day its source gains
authority. Invariant **I11** recomputes every veto that actually happened and
fails if one removed a value its policy protects.

Also decided here: **`R08 UNCONTESTED`**. The resolver used to label a lone
uncontested value `R02 AUTHORITY` when its single source happened to be an
authority and `R04 TIER` otherwise. Both read as though a contest had been
won. 8,975 of 8,975 single-valued facts in Cedar are uncontested; what the
single piece of evidence is worth is carried by `support_status`.

---

## ADR-006 — the handle contract (workstream D)

**Status:** implemented 2026-08-30.

**Context.** Review finding F6. `IDENTIFIER_STANDARD.md` has said since the
day uids were minted that handles change and `cedar_uid` does not. The code
did not implement it: `phase_mint` keyed the existing-uid lookup on the
HANDLE, so a reclassification missed, **minted a second uid for an entity
that already had one**, and dropped the old handle from a register documented
as append-only.

**Decision.** `data/spine/cedar_handle_history.csv` retains every
`(handle, cedar_uid, valid_from, valid_to, status, change_reason)` binding
ever issued. An old handle always resolves to the same uid, through
`503.register_map()` — the map `stamp` keys every dataset with. A retired
handle pointed at a different entity **raises**, it does not warn. A uid is
never dropped from the register, even when its entity leaves the spine.

---

## ADR-007 — a grain declaration is four things, and it is validated (workstream D)

**Status:** implemented 2026-08-30.

**Context.** Review finding F9. `512` recorded grain as `UNSTATED` where no
human had declared it — honest, and useless: such a table still shipped, and a
buyer joining a table whose real grain is entity×UEI×year on `cedar_uid`
alone multiplies every award amount.

**Decision.** A declaration is `grain` + `primary_key` + `join_keys` +
`join_cardinality`, and **every declared field is checked against the file on
every run**. Two different defects, counted separately:

- a **declared grain the data contradicts** is a promise we break —
  release-blocking today through `contract_violations` (MUST_BE_ZERO);
- an **unstated grain on a shippable table** is a promise we never made.
  **207 of 210 shippable tables** are in this state. Failing all of them today
  would make the gate a thing to step around, which standing rule 15 says is
  worse than no gate, so it is **ratcheted**: `contract_grain_unstated_shippable`
  is MUST_NOT_RISE at a floor of 207, and a new shippable table landing
  without a grain fails the gate that day.

---

## ADR-008 — PROPOSAL, NOT IMPLEMENTED: a registrant is a legal person (workstream D)

**Status:** proposed 2026-08-30. Analysis done, implementation not attempted.

**Context.** Review finding F8: "subsidiary UEIs become registrations, never
entities" — so a separately incorporated subsidiary with its own contracts,
liabilities and eventual sale is indistinguishable from its parent. Measured
against live data, this is not a corner case:

| | |
|---|---:|
| live UEI links (non-deny, keyed) | 4,069 |
| entities holding more than one UEI | 443 (max **90** on one) |
| registrations whose **legal name differs** from the entity's canonical name | 3,939 |
| distinct **(entity, differing legal name)** pairs | **3,511** |
| entities holding more than one such name | 421 |
| prime dollars sitting on those registrations | **$173.9B** |
| FPDS parent/child edges where BOTH ends are Cedar-keyed UEIs | 712 |

3,511 candidate legal persons are currently representable only as an
attribute of somebody else, and $173.9B is keyed through them.

**What is NOT proposed.** Promoting every registrant into the entity
universe. Most of those 3,511 names are trading styles, divisions and filing
variants, and a universe that admits them stops being a universe of Native
entities. Automatic promotion would also break the hub model that
`IDENTIFIER_STANDARD.md` exists to protect.

**Proposed instead — the registration becomes a SUB-HUB with its own key,
and nothing is promoted.**

1. Mint a `cedar_registration_uid` per `(identifier_type, identifier)`. It is
   a key, not a membership claim: the registration exists whether or not it
   is a separate legal person.
2. Facts derived from a registration are already qualified with
   `subject_qualifier = "UEI:XXXXXXXXXXXX"` (F7 work, shipped). Re-express
   that qualifier as the registration key, so the fact's subject is the
   sub-hub rather than a string.
3. Add `entity.registration_is_separately_incorporated` as an **assertable,
   refutable** claim with `unknown` as its honest default — never inferred
   from a name mismatch, which is what a trading style looks like too.
4. Transactions key to the **registration**, and roll up to the entity
   through the link. That is what makes a 2027 sale expressible: the link
   gets a `valid_to` (workstream B's bitemporality, ADR-003) and the pre-sale
   awards stay with the registration and stop rolling up to the old parent.

**Why it is not implemented here.** It needs a key minted across 125 stamped
tables and it depends on ADR-003's validity time to be worth anything — a
separate legal person with no interval is still fused to its parent, just
with an extra id. It is recorded as open rather than waved off.
