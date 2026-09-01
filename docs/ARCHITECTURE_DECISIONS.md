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

## Workstream file ownership, pass 2 (2026-08-30, second wave)

The pass-1 table above is EXPIRED. Current owners:

| workstream | owns (may edit) | must not touch |
|---|---|---|
| **E** grain sweep | `code/512_build_dataset_contracts.py` (GRAIN/declarations only), `docs/GRAIN_AUDIT.md`, new grain-evidence outputs | `510`, `514`, `516`, `build.py`, `503` |
| **F** F1 rollout + second source | `code/510_assertions.py`, `code/514_source_records.py`, their docs | `512`, `516`, `62`, `build.py` |
| **G** replay breadth | `code/516_release_manifest.py`, `docs/RELEASE_REPLAY_LOG.md`, `docs/releases/` | all other code |

Shared read-only: `cedar_pipeline.py`, `cedar_codebook.py`, `503`, `62`,
`build.py`. `62` edits route through the integrator this pass. Integrator
commits; no agent commits. The B1 de-hardcode sweep (280 scripts) is
deliberately NOT in this pass - it touches every file and runs solo, next.

**Update 2026-08-29: the solo B1 pass has RUN and debt D1 is closed.** It swept
298 files / 307 occurrences of the project-root literal to 0 unwaived, with one
named exception (`516_release_manifest.py`'s `HARDCODED_ROOT`, which `replay`
needs to rewrite past commits). It ran with no other workstream live, so the
"touches every file" hazard did not materialise. Because it touched every file
it necessarily edited files the table above assigns elsewhere - `516`, `62`,
`293` - and each of those edits is either the mechanical root rewrite or a
direct consequence of it, listed in `docs/RELEASE_REPLAY_LOG.md` §17. The one
substantive change outside the rewrite is in `516`: its input-discovery
resolvers recognised the project root **by matching the literal string**, so
removing the literal would have blinded the only channel that sees NAGPRA's
largest input. They now recognise the derived SHAPE instead (§17c), proven by
comparing resolved path sets across all 414 files: 0 losses, 23 gains.

## Workstream ownership, pass 3 (2026-09-01) — cleanup, learning, universe

Pass-2 table EXPIRED. Current owners:

| ws | owns (may edit) | must not touch |
|---|---|---|
| **H** inventory + known issues | `docs/INVENTORY.md`, `docs/KNOWN_ISSUES.md`, `code/521_inventory.py` | any pipeline, 510, 512, 62, 503, build.py |
| **I** learn from rulings | `docs/NATIVE_ENTITY_NUANCES.md`, `docs/RESOLUTION_RULES_LEARNED.md`, `code/522_mine_rulings.py` | 503, 510, any pipeline |
| **J** spiderweb harvest | `code/523_spiderweb_harvest.py` + its new candidate tables, `docs/SPIDERWEB_LEARNING_PLAN.md` | 503, 510, 512, 62, build.py |
| **K** org universe completeness | `docs/ORG_UNIVERSE_AUDIT.md`, `code/524_universe_gap.py` | the spine, 503, 510, any pipeline |

Nobody commits. Nobody runs `510 --apply` or `build.py ship --execute`.
`NATIVE_ENTITY_NUANCES.md` belongs to **I** alone this pass — K reports gaps
into its own doc and requests nuance edits through its handoff.
Integrator owns 62, 512, 517, 518 and all commits.

## ADR-013 — INCLUSION BASIS is a key (2026-09-01)

**Status:** adopted. The owner:

> "Datasets like federal contracting or federal funding or nonprofits, that's
> where we should probably have a native entity. But all these other datasets,
> we need to know why — because it can look different. We have to know it's
> native for some reason. Maybe it has 'Native American' or something, or maybe
> it was a specific thing related to tribes. When we're pulling bills or
> natural resources, we have to know it's still related to Indian country. And
> if we have established that, **that also counts as a key.**"

This completes ADR-010. Scope says *what kind of thing this record is about*;
**inclusion basis says why the record is in Cedar at all** — and where no
entity can be named, the basis is what a buyer is actually relying on.

Without it, an `indian_country`-scoped row is indistinguishable from a false
positive. A bill in `native_bills.csv` with no entity and no recorded basis is
a claim that the bill concerns Indian Country, backed by nothing.

**Measured 2026-09-01: the practice already exists** — every one of the 13
collections records a basis on at least some tables, several on nearly all
(gaming 43/46, lobbying 27/34, nonprofits 10/10, federal-register 16/22).
Cedar has been doing this by instinct.

**What is missing is standardisation and enforcement:**

1. **A dozen different column names** for one concept — `confidence_tier`,
   `tier`, `basis`, `relevance_tier`, `entity_match_basis`,
   `keyword_terms_matched`, `Record_Scope`, `classification_source`,
   `native_entity_link_basis`, `assignment_basis`. A buyer cannot ask "why is
   this row here" in one query.
2. **Nothing requires it.** `funding` records a basis on 2 of 10 tables,
   `subcontracting` on 2 of 3 — the two datasets whose inclusion is *most*
   mechanical and therefore easiest to leave unstated.
3. **It is not gated**, so a new table can ship with no basis at all.

**Decision — C12, inclusion basis.** Every shippable table must be able to
answer, per row, why the row is in Cedar. One of:

| basis | means |
|---|---|
| `named_entity` | a Cedar entity is a party — the entity id IS the basis |
| `term_match` | matched Native-relevance terms; **the matched terms are recorded**, not just the fact of matching |
| `program_authority` | a tribal-specific program, statute or set-aside (ISDEAA, 8(a) tribal, IHS, BIA) |
| `geographic` | on or near reservation / ANCSA region / a tribal service area |
| `subject_classification` | classified as Indian-Country subject matter, with the classifier and its version |
| `human_ruling` | an owner decision, with its reason |

The **column name may vary** — renaming 5,747 columns to satisfy a schema is
not worth it — but the contract must map each table's existing basis column(s)
to one of these, so the question is answerable uniformly even where the
storage is not uniform.

**Why this matters commercially.** It converts "trust us, these bills are
relevant" into "here is why each row is here." For the datasets that will
never have an entity — legislation especially — the basis is the ONLY evidence
of scope, which makes it the load-bearing column of the whole dataset.

## ADR-011 — what "a clean dataset" means, and C11 column hygiene (2026-09-01)

**Status:** adopted. The owner's definition, in his words:

> "Just having clean datasets is the priority. That identify, if there is one,
> a specific native entity or entities. The rows and data makes sense. We're
> not double counting anything. The data doesn't have weird columns or shit,
> and they all have codebooks associated with them for the variables... we
> don't have to take any dataset for granted. We can make them easier to work
> with, transform some of the variables, because a lot of these datasets are
> wonky. You don't need all the random bullshit codes for prime contracts."

Six requirements. Four were already contract points C1–C10; **two were not**,
and they are added here:

| requirement | where it lives |
|---|---|
| identifies the entity where there is one | C4 + ADR-010 scope |
| rows and data make sense | C1 grain |
| no double counting | C7 |
| codebooks for the variables | C11 (new) |
| no weird columns | C11 (new) |
| **transform wonky source schemas** | C11 (new) |

**C11 — column hygiene.** Measured across 212 shipped tables, 2026-09-01:

```
5,747 columns
  239 ALWAYS EMPTY            dead weight a buyer must ask about
  122 in no codebook           4% - better than feared, still 122 unexplained
```

Worst offenders: `federal_funding_transactions` (13 empty of 58),
`grantmaker_funding_flows` (15 of 60), `resource_assets` (10 of 45),
`deals_classified` (17 undocumented of 52).

**The principle that makes this more than tidying:** *we do not have to take a
source schema for granted.* A federal extract is designed for the agency that
publishes it, not for someone analysing Indian Country. Carrying its codes
through unchanged is not fidelity, it is laziness dressed as fidelity —
provided the transform is RECORDED. So:

1. A column that is always empty is **dropped**, and the drop is recorded in
   the correction register with its reason. It is not evidence of anything.
2. A raw source code is **decoded into a readable column** and the raw code
   kept beside it when it is the join key to the source. Never decoded away
   silently: a buyer reconciling against the source needs the original.
3. Every surviving column has a codebook entry. No exceptions, and the count
   is gated.

**Reported, not blocking, for now.** C11 is measured and published on the
scoreboard but does not flip a dataset to BLOCKED yet, because dropping a
column changes a shipped schema and that must be a deliberate, per-dataset act
with a register row — not a side effect of a metric turning red.

## ADR-012 — clean first, link later (2026-09-01)

The owner on subaward→prime linkage:

> "Sub awards are hard to connect to the prime contracts, and the sub awards
> have their own ID system... I think we should probably be able to link them,
> but it's a little bit messier. That's a case where we just have all these
> datasets, and then over time we can link them and make them more nuanced.
> But just having clean datasets is the priority."

**Decision.** Cross-dataset linkage is a LATER phase and never a blocker on a
dataset reaching READY. A dataset is clean when it is internally correct —
grain, keys, no double counting, entity attachment where an entity exists,
honest columns. Whether it joins cleanly to a *different* dataset is a
separate, subsequent question.

This is why `subawards` having no usable event id (measured: 31,078 collisions
survive the best three-column key we hold) is registered as MISSING rather
than solved by minting a surrogate. A surrogate over a non-unique key would
manufacture 31,078 false distinctions and would make the eventual prime-link
harder, not easier. Diagnose the source extract; do not paper the key.

## ADR-010 — RECORD SCOPE: not every record has one Native entity (2026-09-01)

**Status:** adopted, and it CORRECTS ADR-009's measurement. Owner's framing:

> "Some of these datasets are not gonna connect to a specific native entity
> necessarily. Like, the votes impact probably in most cases all of Indian
> country... you have these multi-coalition, like NARF or NCAI, that are
> advocating on behalf of all of Indian country. We're focused on Indian
> country broadly, so that's why we have nonprofits who may serve natives or
> give to native causes but aren't native. And to the extent we can get to the
> specific native entity, otherwise if they're just valuable in and of
> themselves... if there's a geographic dimension, maybe we can include that."

**The defect this fixes.** ADR-009 made attachment measurable and then treated
every unkeyed row as a failure. That conflates two completely different things:

    "we could not identify the entity"        <- a defect, work to do
    "there is no single entity to identify"   <- the correct representation

A bill that changes federal Indian law affects all 574 federally recognized
tribes. NCAI lobbying on behalf of Indian Country is not an unresolved link to
one tribe. A foundation that funds Native causes is not itself Native. Under
ADR-009 as written, `legislation` would be pushed toward inventing an entity
attribution to clear a blocker — the exact failure the Prime Directive forbids.

**Decision.** Every record carries a `record_scope`:

| scope | meaning | entity attachment |
|---|---|---|
| `entity` | about one Native entity | one `cedar_uid`, required |
| `multi_entity` | about several, named | a party bridge, ≥2 |
| `indian_country` | general applicability | **none, and that is correct** |
| `geographic` | a region, state or BIA area | an area code, not an entity |
| `native_serving` | actor is not Native but the money or effect is | the Native counterparty where one exists; the actor stays unkeyed **on purpose** |
| `unresolved` | we believe an entity exists and have not found it | **the only scope that is a defect** |

`unresolved` is the work queue. The rest are answers.

**Consequences.**

1. **Coverage is measured against the resolvable denominator**, not the row
   count. "40% keyed" is meaningless if half those rows are
   `indian_country` by nature. The honest metric is
   `entity-scoped rows that carry a uid / entity-scoped rows`.
2. **`native_serving` is deliberate scope, not a gap.** Cedar covers Indian
   Country broadly: a non-Native foundation granting to Native causes belongs
   in the data, and forcing a Native uid onto the grantor would be false.
3. **Geography is a first-class fallback.** Where an entity cannot be named but
   a place can, record the place. A record scoped to a BIA region or a state
   is more useful than one scoped to nothing.
4. **Datasets differ in their natural scope mix**, and that mix is a property
   of the dataset, not a score. `contractors` should be almost entirely
   `entity`; `legislation` should be mostly `indian_country`; `lobbying` is
   genuinely mixed and that is the interesting thing about it.

**What does NOT change.** Where a specific entity IS nameable, name it — scope
is not an excuse for leaving resolution undone. The test for `indian_country`
is that the record's own subject is general, not that resolution was hard.

## ADR-009 — the entity layer is DATASET 13, not infrastructure (2026-09-01)

**Status:** adopted. Owner's framing, recorded in his words:

> "The big shift is basically focusing on building thirteen datasets,
> essentially, the thirteenth being the native entity layer. That's how we
> queue and everything — rather than having every dataset kind of identify
> native entities but not having everything talk to each other."

**Context.** Cedar grew dataset-first. Each collection learned to recognise
Native entities on its own, and the shared spine arrived afterwards to
reconcile what they had each already decided. The symptoms are all through
this repo: 42 tables under 75% keyed; three ANCSA corporations carrying
"federally recognized" because one harvester resolved on its own; a CAGE alias
equating two distinct Delaware sovereigns because an alias layer was fed
without review; `deals` able to name only one Native party because nothing
required it to speak a shared many-to-many shape.

Every one of those is the same defect: **twelve datasets each doing their own
identification and not talking to each other.**

**Decision.** The entity layer is dataset **13** — a first-class product with a
grain, a contract, a readiness status and a runbook, exactly like the other
twelve. It is not "infrastructure" and it is not internal plumbing. It is the
hub, and the other twelve are spokes that CONSUME it rather than re-deriving
it.

Three consequences, and they have teeth:

1. **Consumption, not re-derivation.** A dataset does not resolve entities. It
   attaches to `cedar_uid` through the identity layer, and where it cannot, it
   records a candidate — it does not invent a local answer. `510`'s
   `harvest_fr_roster` was rewired to work this way on 2026-08-30 and it is
   the pattern; every other harvester still fusing the two claims is debt.

2. **Readiness is capped by the hub.** A spoke cannot be more READY on identity
   than the hub it stands on. The scoreboard now reports this explicitly
   rather than letting a dataset claim clean identity while the layer beneath
   it is unmeasured. This is why dataset 13 is worked FIRST when its state
   blocks others.

3. **The shared shapes live in the hub, not in each spoke.** Multi-party
   bridges at `(record, cedar_uid, role)`, ownership-change events with
   validity intervals, alias history, handle history. Twelve local
   implementations of many-to-many is how `nagpra` ended up correct and
   `deals` ended up singular.

**What this does NOT mean.** The hub does not absorb domain tables. Gaming
facilities stay in gaming. It owns *identity and the relationships between
identities* — who exists, what they are called, what they are, who owns whom,
and when each of those was true.

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
  **207 of 210 shippable tables** were in this state when this ADR was
  written. Failing all of them at once would make the gate a thing to step
  around, which standing rule 15 says is worse than no gate, so it is
  **ratcheted**: `contract_grain_unstated_shippable` is MUST_NOT_RISE, and a
  new shippable table landing without a grain fails the gate that day.

  **The ratchet did what it was built to do. Re-measured 2026-09-01
  (workstream H): the floor is now 25, not 207.** Workstream E's grain sweep
  tested candidate keys against the FULL file for every one of the 207 and
  landed **185 DECLARED_VALIDATED · 12 OPEN_WITH_EVIDENCE · 13 DEFECTIVE · 0
  unexplained**. Live: `contract_grain_unstated_shippable = 25`,
  `contract_grain_stated_shippable = 185`, `contract_violations = 0`, and
  `data/clean/_regression_baseline.json` carries 25 as the floor. The 12
  needing a human are in `review/OWNER_DECISION_QUEUE.md` §4; the 13 needing a
  pipeline fix are §4b and `docs/KNOWN_ISSUES.md`. Evidence per table:
  `docs/GRAIN_AUDIT.md` and `docs/schema/grain_evidence.json`.

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
