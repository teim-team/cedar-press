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

## Workstream ownership, pass 4 (2026-09-01) — ACQUISITION, not hygiene

Owner: *"I'm concerned because it seems like you're missing stuff for every
dataset."* He is right. The 418-item punch list is entirely hygiene; not one
line says "get the missing years". This pass is acquisition.

| ws | dataset | owns | job |
|---|---|---|---|
| **L** | subcontracting | `code/121_pull_subawards_api.py`, subaward tables | pull FY2022-24, which its own line 21 says were NEVER SUBMITTED |
| **M** | gaming | gaming pullers + `docs/datasets/gaming_sources.md` | enumerate the source surface, then fetch what is missing |
| **N** | lobbying | lobbying/beyond-LDA pullers + `docs/datasets/lobbying_sources.md` | same, with emphasis on non-LDA channels |
| **O** | natural-resources | resource pullers + `docs/datasets/natural_resources_sources.md` | same; ONRR through 2026 and the unbuilt states |
| **P** | native-owned-businesses | `data/staging/business_registry/`, the TERO harvest | scrape 16 of the 18 found lists; promote 544 staged to clean |

**No new general-purpose scripts.** One clean puller per dataset, reusing what
exists. The owner asked for this explicitly.
Nobody commits. Nobody runs `510 --apply` or `build.py ship --execute`.
Integrator owns 62, 503, 510, 512, 517, 518, 526, 527 and all commits.

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

<!-- BEGIN ADR-014 -->
## ADR-014 — the constellation: `serves` is an edge, not a category (workstream INT)

**Status:** accepted 2026-09-01. Owner's framing, verbatim:

> *"We have the concept of hub and sub hub, but there's also the idea that,
> like, this tribal college might not literally be owned by the tribe, but
> serve predominantly that tribal community. So we can see that they're
> connected... if we have IHS facilities or something, the tribe's not
> literally gonna own them. They might manage them... So we don't have to have
> an all native category. We can have, like, serves this community."*

**The problem this names.** Hub-and-sub-hub is an OWNERSHIP relation. It is
exact and it is narrow: Ho-Chunk Inc is a sub-hub of the Winnebago Tribe
because the Tribe owns it. Everything Cedar could not fit into that relation
fell into a catch-all — and the catch-all is measurably where the data goes to
die. `record_scope = native_serving` is declared in ADR-010 and used by
**zero rows**, while **8,138 rows sit in `unresolved`**. "Native-serving" as a
category says only *we could not tie this to anyone*. It is an admission
wearing the costume of a fact.

**The decision.** Affiliation becomes a second edge type alongside ownership,
with its own evidence tier. A constellation is a hub plus everything that
holds a `serves` edge to it, whoever owns those things.

    OWNS       hub -> sub-hub      existing, unchanged
    SERVES     any entity -> hub   new, tiered, many-to-many

**`serves` is many-to-many and that is the point.** A regional Native nonprofit
serving twelve tribes gets twelve edges. Forcing it onto one attribution is the
error the catch-all was invented to avoid; the edge lets us stop choosing.

**The tiers, strongest first.** Nothing is promoted a tier by resemblance:

| tier | basis | example |
|---|---|---|
| `chartered_by` | the instrument names the nation | a tribally chartered college |
| `managed_under_contract` | ISDEAA 638 / self-governance compact | a tribe operating an IHS facility it does not own |
| `registered_with` | the NATION's own office attests the entity | a TERO certification (see Amendment 1) |
| `declares_service_to` | the entity's own words name the nation | a 990 mission statement |
| `located_within` | geocoded inside a named AIANNH area | a nonprofit on the reservation |
| `sole_entity_in_area` | exactly one Native entity in the geography | **inference — never alone** |

### Amendment 1 — `registered_with`, adopted 2026-09-02, at rank 3

**This tier arrived from implementation, not from design.** It is recorded
that way on purpose. The ADR was written with five tiers; the build that
implemented it (`code/851_build_constellation_edges.py`, 2026-09-01) found
that the single largest evidenced pool in the whole unresolved backlog fitted
none of them, wrote those rows under a sixth name, and — instead of quietly
widening the spec — flagged every one of them `tier_is_adr014 = N` so the
decision would have to be taken deliberately. This is that decision.

**What the evidence actually is.** 2,216 edges, and every one of them is a
nation's OWN office publishing the entity's name: a TERO certification, a
tribal business-licence register, an Indian-preference vendor list, an ANCSA
shareholder business directory. TERO is the paradigm case — the Tribal
Employment Rights Office of the nation itself certifies that a firm meets its
Indian-preference standard and prints the firm on its list.

**Why the original five could not hold it, and why the omission was
structural rather than an oversight.** Four of the five tiers are evidenced by
the ENTITY — its charter, its contract, its own words — and the fifth by a
polygon. The ladder had no rung facing the other direction, for **the nation's
own instrument naming the entity**. That is not a weaker kind of
self-declaration. It is a stronger kind, and the omission would have kept
recurring.

**Why rank 3, between `managed_under_contract` and `declares_service_to`.**

* Below `managed_under_contract` (rank 2). A 638 contract or a self-governance
  compact is a *federal* instrument transferring the operation of a programme.
  A TERO certificate is a *tribal* instrument recognising a relationship. Both
  are real; the contract is the heavier one, and it is the one whose absence
  ADR-014 was written to stop papering over.
* Above `declares_service_to` (rank 4). This is the owner's own ordering:
  *"affiliated with is better"* than a firm's account of itself. A 990 mission
  statement is the entity talking about the entity. A TERO listing is the
  sovereign talking about the entity, and only the sovereign can say who is
  certified with it. When the two disagree, the nation's office wins.

**What it is still not.** `registered_with` is a `serves` edge and rule 1
binds it exactly as it binds the others: it is **not** an ownership claim and
**no money rolls through it**. A firm on a nation's TERO list is not a
subsidiary of that nation and its contract awards are not that nation's
revenue. Note also that `directory_type = subsidiary_directory` rows are
refused from this tier entirely and routed to the OWNS layer, because a parent
asserting a subsidiary is ownership and belongs to the relation ADR-014 sits
beside rather than replaces.

### Amendment 1a — three things the extension found wrong here

Recorded because ADR-014 is a specification, not scripture, and the next agent
should not have to rediscover them. Full evidence in
`code/852_extend_constellation_edges.py` and
`docs/CONSTELLATION_EXTENSION_LOG.md`.

1. **`sole_entity_in_area` should be demoted from tier to corroborator.** Two
   builds have now computed it; 27 edges cite it and **zero** rest on it,
   because rule 2 forbids that and the data never offered a case where it
   would have been the honest answer anyway. Listing it as a tier invites
   someone to try to use it as one.
2. **The hub class list excludes nations that charter things.** `HUB_CLASSES`
   does not admit `Federal-level constituency entity`, of which Cedar holds 22
   — the six component bands of the Minnesota Chippewa Tribe, Ramah Navajo
   Chapter, the Paiute Indian Tribe of Utah bands, the Te-Moak bands, both
   Passamaquoddy reservations. AIHEC prints *"The White Earth Reservation
   Tribal Council established the White Earth Tribal and Community College in
   1997"*, which is the strongest evidence this ADR defines, and the edge
   cannot be written because White Earth is not an allowed hub. Refused and
   counted as `hub_class_excludes_constituency_entity` rather than widened,
   because widening touches every route. **This is an owner decision.**
3. **`declares_service_to` cannot be read off a filer's own legal name.** The
   tier says "the entity's own words name the nation", and a 990 filer's legal
   name is its own words — so the route was built and measured against the
   unresolved Schedule C backlog. It resolves 281 EINs and awards ONONDAGA
   GOLF AND COUNTRY CLUB, CAYUGA WINE TRAIL INC and WEST SENECA SOCCER CLUB.
   In upstate New York, Oklahoma and Florida the nation's name is also the
   county's name, and a legal name cannot separate them. The route is refused
   wholesale, with all 281 written to the refusals file so the experiment is
   not repeated.

**Three rules that keep this honest.**

1. **A `serves` edge is never an ownership claim and never rolls into a
   nation's money.** IHS hospital obligations do not become tribal revenue
   because a tribe manages the hospital. Same fence as the gaming
   self-published assertions: the edge travels, the dollars do not.
2. **`sole_entity_in_area` never stands alone.** One tribe in a county is a
   reason to look, not a finding. It may corroborate another tier; it may
   never be the only evidence on an edge.
3. **Geography is a ladder, not a gate** (ENTITY_MATCH_RULES rule 7). An
   entity's own words about who it serves outrank a polygon it sits inside.

**What this buys.** `native_serving` stops being a shrug. A row that today
reads *unresolved* can read *serves the Navajo Nation, tier
`declares_service_to`* — a specific, checkable, refutable claim. That is a
product answer to "which organisations serve my community?", which no catch-all
category can answer at all.
<!-- END ADR-014 -->

<!-- BEGIN ADR-015 -->
## ADR-015 — geography is the second axis, and Cedar Grove owns the picture (workstream INT)

**Status:** accepted 2026-09-02. Owner's framing:

> *"Geography helps us identify the flow of money as a filter of who... we can
> have it entity based and geography based. We don't have to have a fancy data
> visualization in Cedar Press. That's what Cedar Grove is for. But then in
> Cedar Grove, we could do fancier stuff of, like, here's the money flowing to
> this area. Here's how much went to the entities in the area. So then you can
> kinda subtract the difference."*

**The division of labour, decided.** Cedar Press carries the **coding**; Cedar
Grove renders the **picture**. Press ships a joinable geographic key on every
row that can carry one and no charting code at all. This is a boundary, not a
staging order — a map in Press would duplicate Grove and rot.

**The measure this exists to make possible.** Two sums over the same geography:

    money flowing TO an area      sum by PLACE OF PERFORMANCE
    money reaching ENTITIES there sum by RECIPIENT, where recipient is a
                                  Native entity in the constellation (ADR-014)
    the difference                federal money landing in Indian Country
                                  that does not reach Native entities

That difference is a finding, not a byproduct. Nothing else Cedar builds
answers it, and it is the natural pair to the constellation: ADR-014 says who
serves a community, this says what reaches it.

**Current state, measured 2026-09-02 across `data/clean/`:**

| | rows | share |
|---|---:|---:|
| in tables carrying any location column | 7,501,882 | |
| carry a PLACE (city / state / zip) | 7,399,905 | 99% |
| carry a JOINABLE key (fips / geoid / aiannh) | **1,070** | **0.0%** |

So the axis is, today, unbuilt: addresses on nearly everything and almost
nothing to join them to. Two tables are joinable — `gaming_property_locations`
(county_fips, census_tract) and `resource_assets` (fips_code).

**The unlock is already on disk.** `data/raw/contracts/usaspending_gapfill_2026-08-05/`
holds 1,110,938 rows over 1,041,147 distinct award keys carrying, at ~98.5% fill,
both `prime_award_summary_recipient_county_fips_code` **and**
`prime_award_summary_place_of_performance_county_fips_code`, plus state FIPS and
county names. Zero downloads. This is the same corpus that was found to carry
the missing PSC and award-description fields.

**Four rules, because the obvious errors here are expensive.**

1. **Place of performance is not recipient location.** The two FIPS columns
   answer different questions and the difference measure needs both kept
   apart. Collapsing them to one "county" column destroys the measure this
   ADR exists for.
2. **A county is not a reservation.** County FIPS is coarser than AIANNH:
   reservations span counties and counties contain fractions of reservations.
   A county-level difference is an approximation and must be published saying
   so. AIANNH is the better key where it can be had.
3. **The difference is not always positive or meaningful.** An entity
   headquartered outside an area can perform work inside it. Publish the two
   sums; let the difference be derived, labelled, and bounded.
4. **Geographic keys never license cross-dataset summation.**
   `MONEY_TOTALLING_RULES.md` still governs. A shared county code is not
   permission to add a subaward to a prime.
<!-- END ADR-015 -->

<!-- BEGIN ADR-016 -->
## ADR-016 — file ownership for the READY-four promotion pass (workstream PROMOTE, 2026-09-02)

**Status:** accepted 2026-09-02. Declared BEFORE editing, per AGENTS.md
*Parallel agents*.

This pass promotes columns that are already on this machine into the four
datasets `518_dataset_readiness.py` reports READY: `contractors`, `deals`,
`nonprofits`, `native-owned-businesses`. It downloads nothing.

**Files this workstream owns for the duration of the pass**

| file | what is written | script |
|---|---|---|
| `data/clean/prime_contracts.csv` | **9 new columns only**, appended right of the existing 47. No existing column is read-modified. | `code/950_promote_contract_attributes.py` |
| `data/clean/np_orgs.csv` | 3 new columns (`disposition`, `disposition_basis`, `generic_token_match_flag`) | `code/952_nonprofit_disposition.py` |
| `data/clean/native_owned_businesses.csv` | 4 new columns (ISO date + basis, service-category promotion, identifier candidate) | `code/953_nob_normalize_and_key.py` |
| `code/770_sample_extracts.py` | the `SHOW` lists for those four datasets only | — |

**Explicit non-overlap with ADR-015 (workstream INT, geography).** ADR-015 draws
recipient / place-of-performance county FIPS from the same
`usaspending_gapfill_2026-08-05` corpus. `870_build_geo_crosswalks.py` states in
its own header that *"it writes no key onto any transaction table"* and it was
verified to write only `geo_award_county_crosswalk.csv`,
`geo_place_county_crosswalk.csv` and `geo_county_dim.csv`. **This workstream
therefore takes NAICS / PSC / award description / action date only and touches
no geographic column**, and if INT later enriches `prime_contracts.csv` in
place, 950 is idempotent and re-runnable after it — the ordering is declared in
`cedar_pipeline.KNOWN_ORDERINGS`.

**What a rebuild costs.** `40_build_prime_contracts.py` reverts all nine
columns, exactly as it reverts 207's two. 950 is an in-place enricher and must
run after any rebuild. The `.bak_2026-09-02_pre_950_promote_contract_attributes`
file beside the table is the signal.
**OUTCOME, recorded 2026-09-02 after the pass.** All four datasets are still
READY on `518_dataset_readiness.py`. Every promoted table conserved its rows
and the md5 of its pre-existing fields exactly; each enricher has a `verify`
and a `selftest` that proves the NAMED invariant fires on an injected
violation, and all six exit 0. Full write-up:
**`docs/COLUMN_PROMOTION_LOG_2026-09-02.md`**.

Two amendments to the ownership table above, both honest rather than tidy:

1. **`code/770_sample_extracts.py` was already under concurrent edit** by
   workstream INT-READY when this pass reached it - it had fixed the
   drop-blank-column defect and added `Announced_Value_USD`,
   `parent_contract_number` and `funnel_stage` to `SHOW`. Ownership of that
   file is therefore SHARED for this pass, not exclusive as claimed above.
   This workstream made **additive** edits only, for the columns 950/952/953
   created and that no other agent could have known about, re-reading the
   file immediately before each edit.
2. **The non-overlap with ADR-015 held under test.**
   `871_promote_geo_keys_contracts.py` appended 13 `geo_*` columns to
   `prime_contracts.csv` after 950 wrote its nine, and
   `772_strip_nan_sentinels.py` rewrote `parent_contract_number` in the same
   window. All nine promoted columns survived both, and 950 `verify` re-reads
   all 841,002 archive rows to confirm every promoted value still equals its
   source. A fourth script, `954_register_promoted_columns_codebook.py`,
   registers the 17 new columns in the codebook and is not in the table above
   because it writes only codebook FRAGMENTS, which cannot affect another
   dataset's block.
<!-- END ADR-016 -->

<!-- BEGIN ADR-017 -->
## ADR-017 — the regenerate-defect sweep (workstream REGEN, 2026-09-02)

**Status:** accepted 2026-09-02. Declared BEFORE editing, per AGENTS.md
*Parallel agents*.

Owner, 2026-09-02: *"This whole regenerate business — make sure you update all
the scripts so every code is up to date."* One defect class: a **wholesale
writer** holding a hardcoded `fieldnames` literal, run after an **in-place
enricher** added a column, silently deleting it.

**Files this workstream owns for the duration of the pass** — every edit is to
the writer's `fieldnames` expression and to nothing else. No row logic, no
value logic, no path changes.

| file | edit |
|---|---|
| `code/03_apply_exclusions_and_tier.py` `05_parse_doi_nho_list.py` `07_parse_ancsa_ceiling.py` `15e_finalize_terms.py` `20_build_subcontracts.py` `30_funding_pre2008.py` `75_add_bie_schools_and_uios.py` `79_build_award_level_contracts.py` `89_nigc_map_wayback_universe.py` `105_build_florida_gaming.py` `107_pull_remaining_states.py` `114_pull_prime_archive.py` `146_build_visitor_access_records.py` `330_build_native_owned_businesses.py` `351_rebuild_lobbying_panel_from_corrected_disclosures.py` `417_build_entity_identity_crosswalk.py` | derive the header from the live file instead of declaring it |
| `code/76_build_recognition_history.py` | rename one local variable. No behaviour change. |
| `code/845_regenerate_guard.py` | detector correctness (see below) |
| `code/1074_regenerate_defect_sweep.py` | new, this workstream's triage aid |
| `docs/schema/regenerate_guard_baseline.json` | re-baselined AFTER the fixes |

**Two shared files are touched against the pass-2 read-only rule, both because
the mandate names them.** `code/503_identity.py` — one variable RENAME so the
already-correct carry-forward there is visible to the detector; no logic
change. `code/62_no_regression_check.py` — `845 verify` added to the standing
gate set, additively, in its own block. Both were re-read immediately before
editing. **The integrator should review these two edits first.**

**What a fix costs.** A rebuilder cannot repopulate an enricher's column. The
carried column is therefore written **BLANK and named on stdout**, which is
strictly better than deleted: the schema survives, the consumer's join key
survives, and `cedar_pipeline.enrichers_to_rerun(table)` still names who
refills it. A rebuild still requires the enricher to run after it.
### OUTCOME, recorded 2026-09-02 after the pass

**CSV: `845` reports 0 unsafe writers, down from 51.** Not from 33 - that was
the count v1 could see, and v1 was wrong in both directions.

Measured with the CORRECTED detector against the `.bak` copies of every file
this pass touched, so the two columns are the same instrument:

| | before | after |
|---|---:|---:|
| unsafe CSV writer triples (`845 csv`) | **65** | **0** |
| scripts carrying at least one | 48 | 0 |
| columns a rebuild would have deleted | **355** | 0 |
| writers whose header derives from the in-memory row, not the file | 114 sites, 10 losing a column | **0 losing a column** (see PART 3) |
| of them, pairings that did not exist | 9 of v1's 29 | 0 |
| tables proved to survive a rebuild (`1074 carry`) | - | **63** |
| positional writers with header != row length (`1074 positional`) | 0 of 40 | 0 of 40 |
| markdown docs a rebuild could overwrite | 21 (upper bound) | **7** |

**What the detector got wrong, and why it matters more than the fixes.** v1
paired a `fieldnames` literal with any `.csv` name mentioned ANYWHERE in the
file. Its two worst-ranked findings were both imaginary: `910`'s "62 columns
lost from subawards.csv" was an 11-column review file, and `76`'s "27 columns
lost from federal_actions.csv" was a script that only READS that table. Nine
of 29 findings were phantom pairings. Meanwhile it MISSED 26 real ones,
because it could not see a literal passed as an argument to a `write_csv()`
helper - the commonest writer shape in this repo. **A detector that is loud
about nothing and silent about something teaches people to ignore it.**

v2 resolves the output path through the module's own constants, flow-
sensitively (`main()` in `503` binds `tmp` to four different files; a flat
map let the last binding answer for the first writer and reported the
handle-history writer as destroying the entity spine), scopes literals to the
function that can see them, follows one interprocedural hop into the write
helper, and stops at a parameter that has been re-derived. `845 selftest`
proves all three: the detector FIRES on an injected violation, does NOT fire
on the fix, and does NOT fire on a table the script merely names.

**Two shapes remain, both reported and neither fixed:**

1. ~~**93 writers use `fieldnames=list(rows[0].keys())`.**~~ **CLOSED - see
   PART 3 below.** 114 sites, 10 of which actually lost a column; all ten
   fixed, and class 3 is now in the baseline and rule 17.
2. **7 markdown docs** carry a generator plus hand-edit commits plus headings
   the generator cannot emit. Every number there is an UPPER BOUND.
   `845 regen <doc>` settles one by regenerating and diffing, and restores the
   doc either way. Three were settled that way and are recorded in
   `MD_PROVEN_SAFE` with their evidence. Five in total: `REFRESH_CADENCE.md` (3 changed
   lines, all measurements that moved - and `630` already splices into
   `<!-- CEDAR:CADENCE-MEASURED START -->`, a second marker vocabulary the
   check did not know), `ENTITY_FRESHNESS.md`, `DEPENDENCY_MANIFEST.md`.
   plus `REVIEW_BACKLOG_RULINGS.md` (byte-identical) and
   `docs/datasets/_PUNCHLIST.md`. `DOC_STALENESS.md` regenerates with one
   unpaired removal that is a row which stopped qualifying, not prose, and is
   left flagged rather than asserted safe. `LOBBYING_BUILD_LOG_2026-08-05.md`
   regenerates with **30** unpaired removals and is the one genuine candidate
   the sweep found; it needs a human read, not a script.

   **Two traps `regen` hit and now refuses.** A generator that FAILS TO RUN
   leaves the doc byte-identical, which is this command's strongest PASS -
   `06_build_log_stats_v2.py` exited 2 (it lives in `code/lobbying_pull/`, not
   `code/`) and the doc was reported PROVEN SAFE on a diff that never
   happened. And `scan_md` now RAISES when `git log` returns nothing, because
   an empty history scores every doc at 0 hand edits and prints the markdown
   half as clean; that exact 0 was observed once from inside `62`.

**What a fix costs, measured.** `114_pull_prime_archive.py` is the sharpest
case. `PRIME_FIELDS` is 39 and `prime_contracts.csv` is 70, and index 38 is
`contract_transaction_unique_key` in the literal against `ruling_status` in
the file - so an APPEND under the literal misaligns every field past 38. The
script did not do that: it refused, `sys.exit(5)`, unless the header matched
exactly. Correct, and it also meant the script **could not run at all** once
207 / 843 / 950 / 871 had enriched the table. It now writes the LIVE header
and refuses only if a column it MAPS is missing. Rows it derives carry blanks
in the 31 enricher columns and it names them on stdout; rows it keeps are
untouched.

**Amendments to the ownership table above, both honest rather than tidy:**

1. **`code/503_identity.py` was NOT edited.** The ADR reserved a rename there.
   Fixing the detector's rebound-name blindness was the better repair - it
   clears 503 and every future use of the same pattern - so a shared
   read-only file was left alone.
2. **`code/76_build_recognition_history.py` was NOT edited either**, for the
   same reason: scoping the literal lookup to the function that can see it
   removed the phantom pairing at the source.
3. **`code/62_no_regression_check.py` WAS edited**, additively, as rule 17:
   `regenerate_unsafe_writers` (MUST_NOT_RISE) and
   `regenerate_new_unsafe_writers` (MUST_BE_ZERO, answered from 845's own
   baseline, the same arrangement as 293). The integrator should review this
   edit first.

**Baseline.** `docs/schema/regenerate_guard_baseline.json` was re-recorded
AFTER the fixes and now holds **7 markdown entries and zero CSV entries**.
Nothing of this workstream's making is grandfathered in it.
### PART 3, recorded 2026-09-02 — class 3, the header derived from memory

The outcome above listed `fieldnames=list(rows[0].keys())` as *reported and
not fixed*. It is now measured and closed. **114 sites; 10 that actually lose
a column.**

The whole point is that 104 of them are fine, and a blanket rewrite of 114
would have been 104 edits made for nothing plus 104 chances to break a working
build. The pattern is a defect only where all three hold: the script writes a
table that already exists in `data/clean/` or `data/spine/`, that table carries
a column something else added, and the in-memory rows do not carry it.

| verdict | n | what it means |
|---|---:|---|
| **LOSES** | **9** | measured against the live header. Fixed. |
| **UNDETERMINED** | 1 | `82`'s two `**{f"latest_{m}": ...}` spreads. Fixed too - and the guard was right to refuse to guess: read by hand, the real loss was one column, not the 21 a naive count would have claimed. |
| read-modify-write | 5 | `rows = read_csv(P)` then rewrite `P`. The keys ARE the live header. **This is the correct idiom**, not a defect. |
| writes a live table, loses nothing | 8 | |
| writes no shipped table | 91 | a fresh table the script owns outright. Nothing to preserve. |

**The ten:** `82_build_gaming_property_dataset.py` (x2 — capacity history lost
the six `entity_*` link columns; `gaming_properties.csv` lost `cedar_uid`),
`122_ocr_ordinance_scans.py` (5), `151_rebuild_entity_evidence_profile.py` (2),
and `cedar_uid` from `57`, `58`, `66`, `75`, `79`, `127`.

**`79_build_award_level_contracts.py` was half-converted and this caught it.**
Part 1 fixed its `PUBLISHED` literal writing `prime_contracts_published.csv`
and left the sibling writer four lines above emitting
`prime_contracts_awards.csv` from `list(awards[0].keys())`. One script, two
writers, one fixed. Both now derive.

**Four detector defects were found by building this, and all four are in the
field guide's section-3 table** rather than only here, because each is a shape
that recurs:

1. **`845` v1 paired on name overlap, not the output path** — 9 phantom
   findings of 29, 26 real ones invisible.
2. **A regen-and-diff check reads a generator that FAILED TO RUN as a PASS.**
   `06_build_log_stats_v2.py` exited 2 and its doc was reported PROVEN SAFE.
   *Any* regenerate-and-diff in this repo has that hole.
3. **`scan_md` scored every doc at 0 when `git log` returned nothing** — an
   empty history printing a clean bill, observed from inside `62`.
4. **`awards, stats = [], Counter()`** — a tuple bound to a tuple made six
   fully-knowable key sets read UNDETERMINED.

The habit they earn is now habit 4 in the field guide: **an absence of evidence
must never print as evidence of absence.** Check the exit code, check the input
is non-empty, emit UNMEASURED rather than a number.

**The guard now recognises its own fix structurally.** `carry_forward_funcs()`
finds any function that reads a csv header and returns a concatenation, so a
wrapped writer reads as safe without being registered by name — and the next
agent's own helper is understood for free. Without it the guard flagged all
ten repairs as fresh defects.

**`845 selftest` now carries six assertions**, three of them new: class 3 FIRES
on an in-memory writer that drops a live column; it does NOT fire once wrapped
in a carry-forward; and a read-modify-write on the same file reads as CORRECT.

**Markdown, finished.** 21 (upper bound) → **3**. Ten docs settled by actually
regenerating and diffing, recorded in `MD_PROVEN_SAFE` with their evidence.
`docs/LOBBYING_BUILD_LOG_2026-08-05.md` — the one genuine candidate — is
**"the generator is right and the prose is stale"**: 35 removed lines, 30 of
them unpaired, and **every single one carries a number** with a numeric
counterpart on the added side (39,448 → 40,968 raw filings; the ambiguous
queue 361 → 5 because the rulings were applied). `regen` now counts removed
lines containing no digit at all, which is the shape of a sentence somebody
wrote, and reports zero here.

**The three left are not mine to settle.** `DATASET_READINESS.md` (518),
`GRAIN_AUDIT.md` and `DATASET_CONTRACTS.md` (512) are written by
integrator-owned generators and were deliberately not run. `INVENTORY.md`
(521) was slow rather than owned, and is now settled.

**Baseline** re-recorded after the fixes: **0 class 1, 0 class 3, 3 markdown** — `DATASET_READINESS.md` (518), `GRAIN_AUDIT.md` and `DATASET_CONTRACTS.md` (512). All three are written by integrator-owned generators, which this pass deliberately did not run. Every other doc was settled by measurement.

`docs/INVENTORY.md` was the last one settled: **205 vanished lines and every one carries a number**, so the rebuild recomputes them and the LIVE doc is the stale one. It is also the case that produced the no-digit test's own counter-example — the 20 lines that test called prose were blank lines and repeated markdown table headers, all still present in the rebuild.
### PART 3b — two more ways `regen` said SAFE without measuring anything

Both found while closing class 3, both now in the field guide's section-3
table, because the shape recurs far outside this workstream.

**1. `regen` invoked every generator BARE.** `1020_tail_web_probe.py` writes
`docs/COVERAGE_TAIL_SHARD_N.md` under its `doc` subcommand and runs a
**network probe ladder** with no arguments. Regenerating that doc the obvious
way would have opened sockets nobody asked for, in another workstream's
territory. `845 regen <doc> [mode]` now takes the mode, and refuses to run
bare **only** where the doc write sits behind a named subcommand — refusing on
*any* subcommand was too blunt and blocked `527_doc_staleness.py`, which
advertises `verify` and still writes its doc by default. Blocking the honest
test on most generators is worse than the hazard it guards.

**2. "a removed line with no digit is prose" was the wrong measure.**
`docs/INVENTORY.md` reported 20 such lines; every one was a blank line or a
repeated markdown table header. Replaced with the measure that is actually
about deletion: **a removed line whose exact text appears NOWHERE in the
regenerated document.** That is immune to reordering and to hunks that stop
pairing when several adjacent measured lines all change at once, which is what
produced 30 phantom "unpaired removals" on the lobbying log and 48 on the
inventory.

**And rule 17 caught a live one, from another workstream, the same hour.**
`docs/COVERAGE_TAIL_SHARD_N.md` landed after the first baseline and `845
verify` failed on it by name. It was settled by MEASURING — `845 regen
docs/COVERAGE_TAIL_SHARD_N.md doc`, byte-identical — and **not** by
re-baselining it away. That is the whole point of the gate, and it worked on
its first live encounter with something nobody had declared.
<!-- END ADR-017 -->

<!-- BEGIN ADR-018 -->
## ADR-018 — the product-descriptor flagship check (workstream PR29-LOOP, 2026-09-02)

**Status:** accepted 2026-09-02. Declared BEFORE editing, per AGENTS.md
*Parallel agents*.

This workstream owns the Codex loop on `teim-team/cedar-press` PR #29 and the
two generators that feed it.

| file | what is written | script |
|---|---|---|
| `code/760_collection_descriptors.py` | the flagship-consistency check and its `selftest` | — |
| `dist/collection_descriptors*.json`, `dist/samples/*` | regenerated, never hand-edited | 760 / 770 |
| `docs/CODEX_REVIEW_LOG.md` | appended, one section per cycle | — |

**Files this workstream deliberately does NOT run or edit:**
`code/500_build_architecture_map.py`, `code/512_build_dataset_contracts.py`,
`code/518_dataset_readiness.py`. They are integrator-owned (ADR-017 records the
same refusal). The defect below **originates in 500** and is therefore
escalated with its measurement rather than fixed here.

### The defect this ADR exists to declare

`dist/collection_descriptors.json` shipped `owned` as **`"1,657 rows"`** while
`dist/samples/README.md`, in the same directory, states the same dataset as
**2,916 rows** — because `770.FLAGSHIP` draws the customer's sample from
`native_owned_businesses.csv` (2,916 rows, 21 certifying authorities) and
`760.rows_in()` sums only the tables the collection *contract* claims, which
are six `individual_native_*` tables totalling 1,657 and do not include the
directory. `500.COLLECTIONS` matches this collection with
`^(individual_native|tribal_certification)`; the namesake table matches
neither. It has been a known orphan since 2026-09-01 —
`code/730_ws4_grain_money_conservation.py:852` lists it under
`contract_orphan_shippable = 6`, attributed to "the workstreams that
registered them" — and nobody connected it to what the product publishes.

**A sum over a dataset's tables can never be smaller than one of its tables.**
That is the invariant 760 now enforces, and it is the cheapest possible
statement of the bug.

The consequence is larger than the row count. `native-owned-businesses` is
reported READY with `c4_identity_path = 100% keyed` and `c1_grain = 6/6`,
measured across the six tables that exclude the directory. Measured on the
directory itself: `business_entity_id` is filled on **4 of 2,916 rows
(0.1%)**; `nation_id` on 2,725 (93.4%); grain is `UNSTATED`. The dataset is
not READY on the table the customer is shown.

**Widening the collection is an integrator/owner decision**, because it moves
a dataset's readiness and adds four tables (`native_owned_businesses.csv`
2,916, `native_business_contract_links.csv` 2,393,
`native_business_identifier_crosswalk.csv` 481,
`native_business_contracting_by_nation.csv` 18) with no declared grain or key.
Filed in `review/OWNER_DECISION_QUEUE.md`.
<!-- END ADR-018 -->

<!-- BEGIN ADR-022-TRIBAL-DEBT -->
## ADR-022 — tribal debt: the registered-fund holdings seam, and one boundary crossed on purpose (workstream TRIBAL-DEBT, 2026-09-02)

**Status:** accepted 2026-09-02. Declared before editing, per AGENTS.md
*Parallel agents*. Build record: `docs/TRIBAL_DEBT_HOLDINGS_BUILD_LOG.md`.

**What this workstream owns:** `code/1082_tribal_debt_holdings_disclosure.py`
(claimed atomically via `1050 claim`), the new staged tables
`data/staging/tribal_debt_{holdings,obligors,distress_events}.csv` and
`data/staging/tribal_obligor_property_revenue.csv`, everything under
`review/1082_*`, and the cache `data/raw/external/tribal_debt_1082/`.

**Shared files touched, each by the sanctioned route only:**

| file | how |
|---|---|
| `docs/MONEY_TOTALLING_RULES.md` | APPENDED inside a new `TRIBAL-DEBT` marked block. No other block read or written. The block's own prose deliberately avoids writing the literal marker syntax a second time, because two pairs with one name are one block to `574`'s preserver. |
| `review/OWNER_DECISION_QUEUE.md` | APPENDED item **TD-1** (the MSRB EMMA licence decision), per the append-only convention in `START_HERE.md`. |
| `docs/ARCHITECTURE_DECISIONS.md` | this block. |

**Not touched:** `data/clean/` (nothing edited — the deals and gaming tables are
staged against, never written), `code/62`, `512`, `517`, `518` (integrator's),
and `code/1030_sec_edgar_native_transactions.py` (another workstream's; 1082
READS its manifest and candidate index and writes nothing back).

### The boundary crossed, and why

`code/1080_sec_gaming_facility_revenue.py` was claimed on 2026-09-02 for public
casino **MANAGERS'** SEC filings. It is still an unimplemented placeholder and
its agent was killed by a session limit.

1082 takes **per-property revenue from tribal OBLIGORS' own SEC filings** —
Mohegan Tribal Gaming Authority, Seneca Gaming Corporation and their
per-property subsidiary registrants. The decision, on the coordinator's
instruction:

* These are **not managers**. They are the borrowers, and they file with the SEC
  *because of the debt* — a 144A note with registration rights turns the issuer
  into a reporting company. The revenue disclosure is a downstream consequence
  of the financing, which is this workstream's subject.
* 1080 remains free to take the manager side (Boyd, Penn, Churchill Downs and
  the rest). The seam is split by **who filed**, not by which dataset the number
  lands in, which is the same rule
  `docs/PUBLICATION_POLICY.md` (`TERMS-SCOPE`) uses for terms: *the distinction
  is authorship*.
* If 1080's agent returns, the CIK list in `REVENUE_CIKS` is the exact boundary:
  those seven registrants are 1082's, everything else is 1080's.

### One rule this build earns, and it is not about tribal debt

**A mutation without an assertion is a claim, not a change.** Two `str.replace`
patches silently no-opped on a whitespace mismatch while the patch script
printed `patched` both times, and a code path that had never been installed was
then debugged as though it were failing. Every subsequent patch in this build
asserts its target text is present before replacing it. This is the same shape
as the nine entries in `docs/AGENT_FIELD_GUIDE.md` section 3 — a step that
reported on itself rather than on its effect — and it belongs on that list.
<!-- END ADR-022-TRIBAL-DEBT -->

<!-- BEGIN ADR-019-QUARANTINE -->
## ADR-019 — the ledger's RULING must reach the transaction tables (workstream QUARANTINE, 2026-09-02)

**Status:** accepted 2026-09-02. Declared BEFORE editing, per AGENTS.md
*Parallel agents*. Closes `review/1011_cross_dataset_findings.csv` **CDR-11**
and **CDR-12**.

**The decision.** `prime_contracts.attribution_method` records the JOIN — which
identifier column matched — and nothing anywhere records the RULING, which is
how that identifier came to be attached to a nation. So a `cluster_v3` guess
whose own `tier_rationale` reads *"Algorithmic name clustering, unreviewed"* is
byte-identical, to every consumer, to an owner ruling. **A column that records
the join while hiding the ruling is the defect.** From this pass on, the
identity ledger's method and tier travel with the transaction:

    identifier_ruling_method / _tier / _quarantined / _basis / _review

`attribution_method` is NOT changed. It is the correct answer to its own
question and the evidence of which leg the join came down.

**Files this workstream owns for the duration of the pass**

| file | what is written | script |
|---|---|---|
| `data/clean/cedar_identifier_ledger_final.csv` | 3 new columns; `confidence_tier` → `X` and `tier_rationale` rewritten on withdrawn rows; `tribe_id`/`canonical_name` on repointed rows | `code/1079_quarantine_method_exposure.py` |
| `data/clean/prime_contracts.csv` | **5 new columns**, appended right of the existing 70; `tribe_id`/`canonical_name`/`attribution_method`/`confidence_tier`/`attributed_flag`/`cedar_uid`/`owner_*` on withdrawn and repointed rows only | ” |
| `data/clean/prime_contracts_archive_backfill.csv` · `_awards.csv` · `_published.csv` | the same withdrawals and repoints, no new columns | ” |
| `data/clean/subawards.csv` | `prime_native_tribe_id` / `sub_native_tribe_id` and their tiers and uids on withdrawn and repointed rows only | ” |

**Non-overlap.** ADR-016 (workstream PROMOTE) appended nine columns to
`prime_contracts.csv` and ADR-015 appended thirteen `geo_*` columns; both
passes are recorded as complete. This pass appends five more to the right of
all of them and **reads no column either pass wrote**, so 950 and 871 remain
idempotent after it. `40_build_prime_contracts.py` reverts all 27 promoted
columns on a rebuild, so 1079 joins 207, 950 and 871 in the enrichers that must
re-run after one; the `.bak_2026-09-02_pre_1079_quarantine_method_exposure`
file beside each table is the signal.

**Three sub-decisions, each of which could have gone the other way.**

1. **A withdrawal is not an exclusion, and this pass mints no `exclusion_id`.**
   `data/spine/cedar_exclusion_rulings.csv` is the owner's register — every
   one of its 123 rows reads `ruled_by = Elijah Moreno` — and rule 8 says an
   agent ruling may not carry the owner's authority. The withdrawal is
   recorded as `confidence_tier = X`, which `40_build_prime_contracts.py`
   line 82 already honours (`tier not in ("A","B")` never attributes) so it
   survives a rebuild, plus a `tier_rationale` that names this script and
   states, in the row itself, that the refusal is of THIS PAIRING and is not a
   claim that the firm is non-Native.
2. **`cross_dataset_propagation` is not accepted as corroboration.** It has
   already carried `cluster_v3`'s output onto CAGE codes at the same hubs
   (`Blue Steel Company` at Blue Lake, `Eagle Butte Cooperative Assn` at Native
   Village of Eagle, `Government & Industrial Supply` at Barrow). Counting it
   would let the defect corroborate itself — the evidence-lineage trap
   `docs/ASSERTION_LAYER.md` names, where two sources agreeing are one source
   twice.
3. **The CAGE leg is measured and flagged but not adjudicated.** CDR-11 scoped
   on UEI rows; the same three methods key 14,149 more prime rows through
   `cage_exact` ($7.25B) and 41,055 through `parent_uei` ($0.49B). All of it is
   now visible in the new columns and written to
   `review/1079_owner_holds_2026-09-02.csv`; only the UEI leg and the CDR-12
   North Wind / LBYD CAGE rows are repaired here. Adjudicating a population in
   the same pass that discovered it is the mistake this repo keeps paying for.
<!-- END ADR-019-QUARANTINE -->

<!-- BEGIN ADR-020-SUBHUB-REGISTERS -->

## ADR-020 — `cedar_nest_id_register.csv` is a SUB-HUB register, not a second entity space. And a blank endpoint is a sub-hub Cedar declined to mint.

*Decided 2026-09-02 by the `_entity_layer` deepening pass
(`code/1098_entity_rel_counterparty.py`). This ADR answers two questions that
were being asked as if they were separate and are one question.*

### The question

1,375 NEST enterprises hold Cedar-minted ids in `data/spine/cedar_nest_id_register.csv`
(1,610 bindings today), and the standing open item asks whether those are
sub-hubs of their owning nation or a parallel identifier space. Separately,
`entity_relationships.csv` has a blank endpoint on **1,772 of 2,292 rows
(77.3%)**, and `AGENTS.md` names that file as the ownership source of truth.

### The decision

**Both are the same fact and the model already answers it.**
`docs/IDENTIFIER_STANDARD.md` §2: the entity is the hub; a thing complex enough
to have its own children and its own facts gets a **sub-hub**; a UEI or a CAGE
identifies a **registration**, and a registration is a sub-hub. So:

| register | grain | prefix | keyed to |
|---|---|---|---|
| `cedar_identity_register.csv` | one row per Native entity (HUB) | `CE-` + class handle | itself |
| `cedar_nest_id_register.csv` | one row per owned ENTERPRISE (SUB-HUB) | `CEDAR-NEST-` | `owner_hub_cedar_uid` -> the spine |
| `gaming_facilities.facility_id` | one row per facility (SUB-HUB) | — | its entity |
| `np_ein_entity_hub` | one row per EIN filer (SUB-HUB) | — | its entity |

`CEDAR-NEST-` is **the enterprise level of the existing sub-hub layer**, exactly
as `facility_id` is the facility level. It is not a parallel entity space, it may
never be joined as if it were one, and a `CEDAR-NEST-` id may not appear where a
`cedar_uid` is expected. Every NEST row already carries `owner_hub_cedar_uid`
into the spine, which is the entire relation; nothing further is needed and
nothing should be minted to express it.

### What follows for the blank endpoints, and why they are not a hole

Measured on the live file, **every one of the 1,772 names its counterparty in
prose, and nothing is unrecoverable**:

| relation | rows | blank side | what the prose holds |
|---|---:|---|---|
| `owned_by` | 1,462 | source | firm legal name **+ UEI (996) or CAGE (466)** |
| `affiliated_with` | 148 | target | the TDHE's published name (7 also blank on the source side) |
| `brand_of` | 106 | source | the brand family **+ its `CEDAR-ALIAS-` id** |
| `operated_by` | 56 | target | "the United States (Dept of the Interior, BIE)" |

**The standing read — *"996 recover a UEI only from prose; 466 recover
nothing"* — is wrong on the 466. They recover a CAGE code.** Recovery on the
ownership edges is 1,462 of 1,462, 100%.

So the blank `source_entity_id` on an `owned_by` edge is **correct**, and the
rows say so themselves: *"No spine entity for the firm and no intermediate
holding layer invented."* Filling it by minting would put 1,462 registrations
into the entity namespace and invert the hub model. A brand family is "a name
family, not a legal person" and the federal government is out of scope for a
register of Native entities.

**The defect was that the identity lived only in an English sentence.** 1098
promotes it into nine declared columns — `counterparty_kind`,
`counterparty_name_as_recorded`, `counterparty_identifier_type`,
`counterparty_identifier`, `counterparty_identity_state` and a
`counterparty_nest_enterprise_id` bridge — with an anti-fabrication invariant
that every promoted value is a **verbatim substring of that row's own `notes`**.

### And the same answer settles the constellation

`cedar_constellation_edges.csv` has a name-only from-side on **2,408 of 3,153
edges (76.4%)** and the standing proposal is to mint them. Measured:

- **2,365 of the 2,408 are `native_owned_businesses` rows at tier
  `registered_with`** — TERO-certified firms — and **all 2,365 already join to
  `native_owned_businesses.business_source_id` through the `from_record_key`
  already on the edge.** They are not unidentified; they are identified by a
  stable directory-row key.
- **186 of them now carry a published federal UEI**, promoted onto the directory
  by `code/1100` from the `1001` crosswalk. *The sweep was extended by
  minting nothing.*
- **278 of them carry `business_name_is_person_name = 1`.** Minting a
  `cedar_uid` per unkeyed from-side would create **278 natural persons in the
  entity register**, which `docs/PUBLICATION_POLICY.md` forbids outright.

**So: do not mint the constellation's from-side.** Carry `from_record_key` and
the federal link. If a class of them is ever minted it is the
`CEDAR-ENT-` individually-Native-owned class, one reviewed row at a time, and
never the 278.

### The bridge, and the one thing it refused

1098 resolves an `owned_by` firm to a NEST enterprise only when both sides agree
on the OWNER: rung 1 published UEI, rung 2 published CAGE, rung 3 the normalised
name unique among the enterprises of that same owner hub. **262 of 1,462 (17.9%)
resolve.** 23 more would resolve through NEST's own `uei_candidate` and are
refused — a candidate on one side plus a candidate on the other is not evidence.

**One resolved on the identifier and disagreed about the owner, and it is the
first cross-source ownership disagreement the entity layer has produced:**
`Laulima Government Solutions, LLC` (UEI `QTJZT9K41S61`) is Bering Straits
Native Corporation in `entity_relationships` (tier A, owner ruling) and
Alaka'ina Foundation in NEST (`parent_declared_subsidiary_list`, source
`http://beringalakaina.com/`). The source host names both parents;
`ENTITY_MATCH_RULES` rule 11 says a joint venture genuinely has two. **Refused,
not reconciled** — `review/entity_rel_nest_owner_conflicts_2026-09-02.csv`.

<!-- END ADR-020-SUBHUB-REGISTERS -->


<!-- BEGIN ADR-021 -->
## ADR-021 — clearing the owner decision queue (workstream DQC, 2026-09-02)

**Status:** accepted 2026-09-02. Declared here rather than before the edits
because DQC ran against files no other pass-4/5 workstream claims; the
exceptions are named below and each was written additively, backed up, and
proved conserved.

**Mandate.** The owner's standing rule, repeated five times: *"I'm not deciding
anything except adjudicating Native entities — you are doing it. Stop asking,
and make corrections and updates and findings."*

### Owned (edited)

`code/1103_decision_queue_clearance.py` ·
`docs/DECISION_QUEUE_CLEARANCE_2026-09-02.md` ·
`data/staging/decision_queue_1103/` ·
`review/OWNER_DECISION_QUEUE.md` (inside `DQC-CLEARANCE-2026-09-02` markers) ·
the eight `review/` queue CSVs listed in the doc.

### Touched outside `review/`, and why each was DQC's to touch

| file | why |
|---|---|
| `data/clean/native_business_contract_links.csv` | the mandate names item C's 35 `WITHHOLD_PENDING_RULING` rows as an owner ruling to APPLY, and the gate column is where it applies |
| `data/clean/native_business_identifier_crosswalk.csv` | same ruling, identifier side |
| `data/clean/anc_ceiling_roster.csv` | the mandate names item 10f and says *label, never delete* |

All three are **additive only** — new columns, no column removed, no row added
or removed, no money column touched — and each carries a
`.bak_2026-09-02_pre_1103_decision_queue_clearance`.

### NOT touched, deliberately

`cedar_identifier_ledger_final.csv`, `cedar_entity_spine.csv`,
`entity_aliases.csv`, `prime_contracts.csv`, `federal_funding_transactions.csv`,
`503_identity.py`, `62`, `512`, `517`, `518`, `build.py`, and
`docs/ENTITY_MATCH_RULES.md`. **A disposition is not a repoint.** Every item
needing one of those is handed over by name in the doc's HANDOVERS table.

### The decision rule this pass adds

**A DECISION MUST BE WRITTEN ONTO THE ROW THAT ASKED FOR IT.** Four of the
eleven `16.x` items had already been decided and were still being presented as
open, because the ruling was recorded in a sibling file, a staging table or a
summary doc rather than on the queue row. An invisible ruling is re-asked. A
pass that cannot write back to the asking row has not finished.

This is the same failure the project already documents for numbers — *"superseded
figures never get overwritten; they sit in the document where they were
written, looking exactly as authoritative as current ones"* — and it costs more,
because a stale number misleads a reader while a stale question consumes a whole
session.

### Two defects DQC committed and caught in itself

Recorded because the field guide's section 3 is about exactly this shape.

1. **The join key was blank.** The first run wrote the earmark dispositions on
   `recipient_name` and left 477 rows unruled — precisely the 477 whose
   recipient cell is empty in the source. The dispositions carried a unique
   `earmark_id` the whole time. A second variant joined subawards on the bare
   name and collided 362 rows onto a sibling's disposition. The joiner now tries
   several candidate keys including composites, **prints which one it used**,
   HOLDs any row whose key carries more than one disposition rather than
   guessing, and refuses to write a file that would look ruled and is not.
2. **The selftest's column-drop case did not fire, and it was right not to.** It
   dropped a column *this script had added*, which the baseline never carried,
   so "no column lost" was the correct answer to the wrong question. It now
   drops a column the baseline actually holds. *Verify your input contains what
   you think it does.*

<!-- END ADR-021 -->

<!-- BEGIN ADR-024-GAMING-NR-DEEP -->
## ADR-024 — file ownership and rebuild ordering for the gaming/natural-resources deepening pass (workstream GAMING-DEEP / NR-DEEP, 2026-09-02)

**Status:** accepted 2026-09-02, declared before editing, per AGENTS.md
*Parallel agents*. This pass downloads seven hosts and nothing else; the rest is
joins and typing against material already on this machine.

**Explicit non-overlap with the two sibling gaming agents.** One owns SEC
filings by public casino managers (`code/1080_sec_gaming_facility_revenue.py`,
`SEC-GAMING` in `MONEY_TOTALLING_RULES.md`); one owns EMMA municipal bond
disclosure. **This pass writes no SEC row, no EMMA row, no CUSIP and no bond
date** — on `tribal_bond_issuances.csv` it writes `issuer_entity_id` and its
five provenance columns and touches nothing else.

| file | what is written | script |
|---|---|---|
| `data/clean/gaming_property_self_published_claims.csv` | 314 appended rows + 12 new columns | `code/1094_merge_web_harvest_into_gaming_claims.py` |
| `data/clean/gaming_property_self_published_assertions.csv` | 861 appended rows + 5 new columns | `code/1094_...` |
| `data/clean/gaming_revenue_bounds.csv` | **5 new columns only.** No dollar cell is read-modified | `code/1095_gaming_bounds_summability_and_seal_typing.py` |
| `data/clean/gaming_facilities.csv` | **3 new columns only.** `960`'s two `state_revenue_disclosure_*` columns are read and NOT changed | `code/1095_...` |
| `code/980_gaming_web_harvest.py` | the three restriction constants, plus `METHOD_RESTRICTED_HOSTS` and its three call sites | `code/1096_navajo_unexclude_and_harvest.py` |
| `data/staging/gaming_web_harvest/{targets.csv,host_probe.jsonl}` | 7 rows flipped; 7 cached refusals MOVED to a dated sidecar | `code/1096_...` |
| `data/clean/resource_revenue.csv` | 2 new columns, never blank | `code/1097_nr_bridge_bonds_and_thirteenth.py` |
| `data/clean/resource_parties.csv` | 60 appended bridge rows | `code/1097_...` |
| `data/clean/tribal_bond_issuances.csv` | `issuer_entity_id` + 5 provenance columns | `code/1097_...` |

**THE REBUILD ORDERING, AND IT IS THE WHOLE RISK OF THIS PASS.** Four of these
tables have a full-rebuild writer. Every script here is an in-place enricher and
**must run LAST**:

| rebuilt by | enricher that must run after |
|---|---|
| `588_promote_self_published_claims.py` | `1094` |
| `106_build_revenue_bounds.py` | `1095` |
| `23d_build_gaming_facilities.py` → `158` → `960` | `1095` |
| `980_gaming_web_harvest.py build` | `1094` |
| `83_build_resource_ledger.py` | `1097` |

**All four enrichers are idempotent and were proven so by re-running them.**
`1094 merge` run twice appended 309 then 0; run again after `980 build` grew the
harvest 1,166 → 1,175 it appended exactly the 9 new rows and its 8 invariants
still passed. That is the ordering working, not surviving.

`cedar_pipeline.KNOWN_ORDERINGS` is shared and read-only for this pass, so those
five pairs are **requested of the integrator**, not written here.

**Every script has `verify` with a `--selftest` that injects the violation and
asserts the NAMED invariant is the one that fires** — 8 + 7 + 4 + 9 = 28
invariants, and each selftest also asserts the clean set fires nothing. All four
exit 0.

**Measured against the gates.** `293_lint_bug_classes.py` names **zero**
instances in `1094`–`1097`. `cedar_pipeline.columns_lost_vs_backup` returns `[]`
for all seven tables. `814_gaming_nr_grain_and_conservation.py verify` exits 0
and still reconciles 421,590 readings → 11,305 published rows, and it
re-validated `claim_id` and `assertion_id` as UNIQUE at their new counts.
`62_no_regression_check.py` is red on 20 metrics; none of them is this pass's,
and the evidence is the three measurements above plus the fact that every named
lint site belongs to `1075`, `1077`, `1080`, `1081`, `1103`, `1104` or `1107` —
concurrent higher-numbered work.
<!-- END ADR-024-GAMING-NR-DEEP -->

<!-- BEGIN ADR-023-NEWSLETTERS -->
## ADR-023 — the newsletter corpus ships as a collection, and the deals out of it do not

*Workstream `newsletters`, 2026-09-02. Scripts `990`, `991`, `995` (owned by
this workstream), `1105` (new), plus a `GRAIN_NEWSLETTER` dict in `512` and one
`COLLECTIONS` entry in `500`.*

### Files this pass owns, and the ones it deliberately did not touch

Owned and edited: `code/990_build_newsletter_corpus.py`,
`code/991_newsletter_gap_sweep.py`, `code/995_write_newsletter_docs.py`,
`code/1105_newsletter_corpus_ship.py`, `code/1106_tribal_election_survey.py`.

Shared files, edited only inside this workstream's own region:
`code/512_build_dataset_contracts.py` (added `GRAIN_NEWSLETTER`; no other
workstream's dict touched), `code/500_build_architecture_map.py` (one
`COLLECTIONS` entry), `code/cedar_pipeline.py` (two `REPLAY_ORDERS` keys, no
change to `NEVER_RUN` or `KNOWN_ORDERINGS`), `docs/MONEY_TOTALLING_RULES.md`
(inside `<!-- BEGIN NEWSLETTERS -->`), this file (inside this marker).

**Not touched:** `62`, `517`, `518`, `293`. Nothing was committed.

### The decision: two tables, and the second one is the product

`tribal_newsletter_corpus.csv` alone is a list of URLs. What makes it a finding
aid is `tribal_newsletter_coverage.csv` — **one row per spine entity, all
1,555, whether or not anything was found**. No published catalogue of tribal
periodicals carries a denominator, which is why none of them can answer *which
nations publish and which do not*. 990's invariant 5 fails the build if the
coverage table ever drifts from the spine, so the denominator cannot quietly
become a sample.

### The decision: absences stay in the corpus, behind a declared discriminator

The corpus holds 1,889 rows and 1,394 publication channels. The difference is
481 recorded absences, one signup form, and 13 flagged place-name collisions.
Keeping the negatives beside the positives is deliberate — a negative from
search alone is not a negative in this project, and `discovery_technique` on an
absence row names which routes ran. But two record types under one schema is
how *"539 publishable coords"* happened, so the unit is declared per row in
**`record_status`**, and 990's invariants 8–10 fail the build if that column and
the data it summarises ever disagree. `995` now reads the channel count off that
column instead of holding its own copy of the vocabulary.

### The decision: the deals extracted from the press are NOT this collection

`data/staging/deals_from_newsletters/MERGE_PROPOSAL.md` holds 258 tier-A
candidates. They belong **inside** `deals_classified.csv`, merged by the agent
who owns that table (stub `1088_merge_staged_deals.py` is claimed for it). As a
standalone dataset they would be a pile of unverified sentences, and the
`newsletters` collection regex `^tribal_newsletter_` deliberately cannot reach
them.

### Two upstream defects this pass found, both by invariant rather than by eye

**1. A Wayback URL outranked a live one, and hid five nations.** 991's site
preference ranked web-map URLs by `url_type` with no preference against
`web.archive.org`, so an archive capture could win — and the wayback skip, which
exists for entities whose ONLY known URL is a snapshot, then fired on entities
whose *first-ranked* one was. Fort Independence, Poarch, Pueblo of Pojoaque,
Redding and Ute Mountain all run live sites that no route had ever touched.
Archive hosts now sort to the back of the preference order.

**2. `has_live_site` was `yes` for 45 nations with no website.** Once archive
URLs were demoted, the next-ranked "website" for 45 Alaska Native Villages was
the **BIA Tribal Leaders Directory ArcGIS FeatureServer query** that shard K had
used to *read* them. A response about you is not a site you operate. Probing it
would have asked a federal API for a newsletter. `site_url_class` now declares
`third_party_api_endpoint`, `wayback_snapshot_only`,
`propublica_irs_profile_only`, `social_media_only` and `no_url_anywhere` beside
`own_live_site`, and 991 skips the API case by name.

Both were surfaced by a new invariant, not by reading the data:
**`PROBEABLE_FRONTIER_NOT_CLOSED`** fails the build if any in-scope entity
operates a live site and has never been probed. "We finished the frontier" is
now a check, not a sentence in a document.

### One check was wrong and was caught before it shipped

The first version of 1105's privacy invariant scanned `note` for private-life
terms and fired on **88 real rows** — all of them Cedar's own description of a
source: *"The Council … carries member-village council news, obituaries and
program notices."* That is not an obituary. Saying a publication carries
obituaries is not extracting one, and a check that deleted those sentences would
have made the corpus less truthful in the name of privacy. Rescoped to the
fields where a leak would actually land — `publication_name`, `channel_url`,
`recent_issue_urls`, where a slug like `/2024/03/obituary-jane-doe/` would
appear. 0 hits, and the selftest asserts both that a planted slug FIRES and that
a descriptive note does NOT.

<!-- END ADR-023-NEWSLETTERS -->

<!-- BEGIN ADR-021-DEALS-MERGE -->
## ADR-021 — file ownership for the staged-deals merge (workstream DEALS-MERGE-1088, 2026-09-02)

**Status:** accepted 2026-09-02. Declared per AGENTS.md *Parallel agents*.

> **MARKER COLLISION FOUND WHILE WRITING THIS, AND NOT CAUSED BY IT.** This
> file already carries **two** blocks named `ADR-018` — PR29-LOOP's
> product-descriptor flagship check at line ~1064 and GAMING-DEEP / NR-DEEP's
> ownership declaration at line ~1426, both accepted 2026-09-02.
> `docs/AGENT_FIELD_GUIDE.md` section 2 is explicit: *"Two blocks sharing a
> marker name are one block to the preserver. Pick a name nobody has."*
> The next wholesale rewrite of this file by its generator will keep one of
> them and silently drop the other. **This is an integrator fix — renaming
> another workstream's accepted ADR is not an agent's call — and it is why
> this block is named `ADR-021-DEALS-MERGE` rather than `ADR-021`.**

**What this workstream owns for this pass:**

| file | how it was touched |
|---|---|
| `code/1088_merge_staged_deals.py` | NEW, claimed atomically via `1050_preflight.py claim` and written into that stub |
| `data/clean/deals_press_edgar_ancsa_additions.csv` | NEW, 144 rows x 32 cols, the tenth `deals_*_additions.csv` slice |
| `data/clean/deals_classified.csv` | append-merge via `88_build_deals_taxonomy.py`, then the in-place enrichers LAST (`126_apply_deal_party_attribution.py`, `503_identity.py stamp --apply`). Backed up to `.bak_2026-09-02_pre_1088_merge_staged_deals` |
| `review/deals_1088_refusals.csv` · `review/deals_1088_disposition.json` · `review/deals_1088_intra_family_retest.csv` | NEW |
| `docs/methodology/deals.md` | new section 5b; header re-measured 935 -> 1,079 with the superseded figure kept and explained |
| `docs/MONEY_TOTALLING_RULES.md` | **inside `<!-- BEGIN DEALS-MERGE-1088 -->` only.** No other block read or written |
| `code/512_build_dataset_contracts.py` | **`GRAIN_DEALS_MERGE` only.** No other workstream's `GRAIN_*` dict touched |
| `review/OWNER_DECISION_QUEUE.md` | appended DM-1 / DM-2 / DM-3 inside `<!-- BEGIN DEALS-MERGE-1088 -->` |

**What it deliberately did NOT touch.** Four sibling agents were working other
datasets in this same session: `nagpra_notices.csv`,
`nagpra_notice_institutions.csv`, `federal_actions.csv`, `bill_votes.csv`,
`native_bills.csv` and `native_entity_lobbying_disclosures.csv` were all left
alone. `cedar_constellation_edges.csv` and `nest_enterprise_relations.csv` were
**READ ONLY**; the two defects found in them are reported in `AGENTS.md`, not
repaired, because they belong to `852` and `1072`.

**Rebuild ordering respected.** `88_build_deals_taxonomy.py` is a full builder
over `deals_*_additions.csv` plus the two root ledgers; `126` and
`503 stamp` are in-place enrichers on the same table. **The enrichers ran
LAST.** `deals_classified.csv` is in `62`'s class-6 list for exactly this
reason, and reversing the order would have reverted the attribution columns the
way `133 build` reverted `168`'s links on 2026-08-26.
<!-- END ADR-021-DEALS-MERGE -->




<!-- BEGIN ADR-023-STANDARD-GUARD -->
## ADR-023 — the punch list is an instruction set, so its claims are gated (workstream STANDARD, 2026-09-02)

**Owner of this block:** workstream STANDARD. Files it touched are listed at the
bottom; nothing else was edited.

### The decision

`docs/datasets/_PUNCHLIST.md` is not a report. Every line is an ACTION WITH A
TARGET, and ten agents work from it concurrently. A false line is therefore not
a stale number — it is an instruction to damage the data. From today the punch
list has a guard that re-measures its own claims against the live files with no
row cap:

    py -3 code/1107_punchlist_claim_verify.py            measure + report
    py -3 code/1107_punchlist_claim_verify.py verify     exit 1 on a false claim
    py -3 code/1107_punchlist_claim_verify.py selftest   proves it fires

It imports `526_dataset_standard.py` and audits the LIVE generator's output, not
the markdown, which is a snapshot.

### Why — 43 of 65 claims on the capped tables were false

`526.scan()` reads at most 20,000 rows and then asserts on that sample that a
column is "always empty in 20,001 rows". Re-counted over the full files:

| table | rows | "always empty" claims | actually empty |
|---|---:|---:|---:|
| `prime_contracts.csv` | 1,217,768 | 10 | **0** |
| `federal_funding_transactions.csv` | 701,955 | 18 | 2 |
| `faads_transactions_all_agencies.csv` | 2,769,748 | 7 | 4 |
| `native_entity_lobbying_disclosures.csv` | 27,825 | 8 | 0 |
| …13 capped tables in total | | 65 | 22 |

`prime_contracts.csv`'s line said *"drop 10 always-empty column(s)"*. Those ten
include `contract_transaction_unique_key` (**841,002 non-blank**, 69.1%),
`contract_award_unique_key` (841,002) and `naics_code` (838,229). An agent who
did what the line says would have deleted the contracting table's award keys and
its NAICS. The current false-claim census is
`docs/datasets/_PUNCHLIST_CLAIM_AUDIT.md`, regenerated with the punch list.

**The rule this earns:** *an instruction may not be issued from a sample.* A
measurement may be sampled if it says so and prints the cap; an instruction to
DROP something may not.

### The second closed loop: no codebook item could close

The punch list carries ~39 items of the form *"write codebook entries for N
column(s)"*, measured against `data/clean/codebook_master.csv`. The sanctioned
way to close one — `392` and `208` both state it — is to write a fragment under
`data/clean/codebook/` and fold it in with `cedar_codebook.py build`. That
fold-in was REFUSING to run: 14 rows sat in the master that no fragment carried
(`07_gaming` ×3, `11d_nagpra_notice_institutions` ×11, both written straight to
the master), and `build` correctly refuses any rebuild that shrinks the
codebook. So an agent could do exactly as instructed and the item would never
close, because the file the punch list measures could not be rebuilt from the
file the agent was told to write.

Repaired by `code/1108_codebook_fragment_repair.py repair`. `cedar_codebook.py
check` now reports **0 lost / 0 added**. Do **not** repair this with
`cedar_codebook.py split`: it writes one fragment per distinct `dataset` value
and two values contain a slash (`06_nonprofit/np_orgs`,
`06_nonprofit/np_financials`), so split would put them in a SUBDIRECTORY where
`build`'s `FRAG.glob("*.csv")` cannot see them.

### A licensing control that measured the wrong thing

`62`'s `duns_marked_publishable` scores `access_tier != "internal"` and never
reads `published`, and it greps the variable NAME for "duns". Two rows walked
through it:

- `07_gaming / casino_city_id` — `published=1`, `access_tier=**public**`,
  description "Identifier." Invisible to `62` because its name has no "duns" in
  it. `START_HERE.md`: *"Casino City may be read for QA and never published."*
- `03_federal_funding / recipient_duns` — `published=1` with
  `access_tier=internal`: a row that contradicts itself, and passes `62`.

Both set to `published=0 / internal` by `1108 fix-licensed`. **The publication
layer was never wrong** — `dist/07_gaming/gaming_facilities.notes.json` already
lists `casino_city_id` under `identity.licensed_columns_withheld`. What was
wrong was the CODEBOOK, which is the document a buyer reads to learn what they
get. `1108 verify` K4 now covers `is_licensed_col`, not a name grep, and reads
both fields.

### Findings handed to the integrator, NOT acted on

`526` is integrator-owned (line 87 of this file), so this pass did not edit it.
The exact patch is at the foot of `docs/datasets/_PUNCHLIST_CLAIM_AUDIT.md`.
Four items, each with its evidence:

1. **C5 cannot be closed by doing the work.** `526` compares
   `source_table.split("/")[-1]`, but the convention in
   `cedar_harvest_conservation.csv` is to QUALIFY the source in brackets —
   `data/clean/np_orgs.csv [IRS BMF rows via np_orgs own cedar_uid link…]` —
   which can never equal `np_orgs.csv`. Two items are already false today
   (`np_orgs.csv`, `cedar_identifier_ledger_final.csv`), and **every future
   conservation row written the way the file already writes them will fail to
   close its item.** C5 is 164 of the 339 open items, so this is the largest
   single blocker on the list.
2. **C12 passes on a field-level provenance basis.**
   `faads_transactions_all_agencies.csv` satisfies the ADR-013 inclusion-basis
   check because the string `tier` appears inside `geo_key_tier` — a county
   geocoding confidence tier, which says nothing about why the row is in Cedar.
   Three tables pass on nothing better than that.
3. **C12 does not read a declared `population_scope`.** Two tables have the
   table-level ADR-013 declaration written in `dataset_contracts.json` and are
   scored as having none. `faads_transactions.csv` is one of them — so the
   table that DECLARED its scope fails while its sibling passes on `geo_key_tier`.
4. **A zero-row or unreadable shippable table is INVISIBLE.** `scan()` returns
   an empty header and every column check is skipped, so the table produces no
   punch items at all and reads clean. One today: `deals_2026_ytd_additions.csv`.

And one that is not the integrator's: `526 verify`'s docstring says *"read-only,
exit 1 on breach"* and `main()` returns 0 unconditionally. **`526 verify` cannot
fail, so it is not a gate.**

### Files this workstream owns for this pass

- `code/1107_punchlist_claim_verify.py`, `code/1108_codebook_fragment_repair.py` (new)
- `docs/datasets/_PUNCHLIST_CLAIM_AUDIT.md`, `docs/datasets/_punchlist_claim_audit.json` (new, generated)
- `data/clean/codebook/*.csv` — 16 fragments, +103 entries, +14 repaired orphans, 2 licensed rows corrected; master rebuilt with `cedar_codebook.py build`
- `code/845_regenerate_guard.py` — `orphan_headings` only, plus three selftest cases
- `code/77_build_nagpra_dataset.py`, `code/511_sam_entity_hierarchy.py`,
  `code/221_probe_regulations_gov_comments.py`,
  `code/110_build_harmonized_views.py` — rule-17 header derivation, one helper each
<!-- END ADR-023-STANDARD-GUARD -->

<!-- BEGIN ADR-023-FR-DTLL -->
# ADR-023 — `federal-register`: the NAGPRA overlap goes on the ROW, and the Dear Tribal Leader letters come from the agencies, not the Federal Register

*Workstream FR-DTLL, 2026-09-02. Scripts `1089` and `1090`, both claimed
through `1050_preflight.py claim`. Every figure below was recounted from the
live files that day.*

## What was owned and what was only read

| file | this workstream |
|---|---|
| `data/clean/consultation_events.csv` | **WRITTEN IN PLACE**, +8 columns, +0 rows, by `1089`. Backup `.bak_2026-09-02_pre_1089_fr_consultation_overlap_and_event_parse`. |
| `data/clean/dear_tribal_leader_letters.csv` | **CREATED** by `1090`, 807 rows. |
| `data/clean/dtll_source_coverage.csv` | **CREATED** by `1090`, 35 rows, internal. |
| `data/clean/nagpra_notices.csv`, `nagpra_notice_entity_bridge.csv` | **READ ONLY.** Another agent is live on `nagpra`. Neither was opened for writing at any point. |
| `code/96_build_consultation_events.py` | **NOT EDITED.** It owns `consultation_events.csv` and rebuilds it; `1089` is registered as its enricher instead. |
| `code/500`, `code/512`, `code/cedar_codebook.py`, `code/cedar_pipeline.py` | registration only, inside a new `GRAIN_FR_DTLL` dict and one new `KNOWN_ORDERINGS` entry. No other workstream's dict was touched. |

## Decision 1 — the overlap is a COLUMN, not a caveat

`consultation_events.csv` is 95.5% `NAGPRA_consultation_reported` and `nagpra`
ships as its own dataset, so a buyer holding both can double-count. The
overlap was known and stated in prose. **Prose does not travel with a CSV.**

`nagpra_notice_overlap`, `nagpra_bridge_overlap` and `nagpra_coverage_window`
now carry it on every row, `fr_document_number` makes it checkable, and
codebook block `09c_consultation_events` states it in the description of both
`consultation_type` and `nagpra_notice_overlap`.

**And the measurement changed the claim.** "95.5% NAGPRA" is a ROW share.
Measured at document grain: 1,831 distinct notices of 2,313 here, against
6,792 in `nagpra_notices.csv` — **4,961 NAGPRA notices are not in this file at
all.** The two tables are not a duplicate pair; they are a 27% intersection
built by two different extractions, which is why the bridge comparison
(`same_notice_different_party` on 1,606 rows) is a review queue worth having.

## Decision 2 — the letters get their own table

`96` rebuilds `consultation_events.csv` from its own two FR inputs, so an
appended DTLL row is dropped on its next run — the `09_import_rulings.py`
shape. `docs/methodology/federal-register.md` already recommends *"build a
THIRD file that reads both and writes neither"* for the Section 106 merge, and
the same answer applies here. `consultation_events.csv` keeps its 6 FR-sourced
rows; the 597 letters that were never FR documents live where a rebuild cannot
reach them.

## Decision 3 — `record_kind`, not a filtered table

The publishers' own indexes carry letters, enclosures and index pages
together. Dropping the enclosures would discard documents the agency
published; counting them as letters would inflate the headline by 35%. Both
ship, `record_kind` separates them, and the grain declaration says **counting
rows counts documents, not letters**.

## The two defects this workstream found in its own first pass

Recorded because both are the repo's signature shape — a check that produced a
plausible number about something else.

1. **A `?page=N` sitemap loop that fails open.** `bia.gov/sitemap.xml` is a
   Drupal `simple_sitemap` INDEX; `?page=3` through `?page=20` return **the
   index itself**, HTTP 200, two `<loc>`s each. The first pass reported
   *"2,412 URLs over 20 pages"* and made 18 pointless requests. It now walks
   the index's own children and refuses any shard that hands back an index.
2. **An unanchored place regex that measured contact addresses.** Filling
   `location` from any `City, State` near a date put 657 museum contact
   addresses and excavation counties into NAGPRA rows. A location is now read
   only from a notice that announces an event. The fill fell from 703 rows to
   43, and 43 is the honest number.

## One publisher signal the owner should see

`www.hud.gov/robots.txt` serves `User-agent: * / Allow: /` — HUD is open — but
it also carries a Cloudflare `Content-Signal: search=yes,ai-train=no,
use=reference` and a list of named AI crawlers (`Amazonbot`,
`Applebot-Extended`, `Bytespider`, and others) under `Disallow: /`. Cedar's use
is reference and aggregation, not model training, so the signal does not
forbid this work — **but it is a publisher stating terms in a place
`urllib.robotparser` cannot see, and the number of federal sites carrying one
will only grow.** Recorded here rather than acted on, because whether Cedar
honours `ai-train=no` beyond its literal scope is an owner decision, not an
agent's.

`www.hud.gov/sitemap.xml` returns **HTTP 404** and `www.hhs.gov/sitemap.xml`
returns **HTTP 403**; both are recorded `NOT_CHECKED` and neither is an
absence. HHS's robots.txt names no `Sitemap:` directive to fall back to.
<!-- END ADR-023-FR-DTLL -->

<!-- BEGIN ADR-SEC-GAMING -->
## ADR-SEC-GAMING - an SEC filing is a THIRD class of gaming evidence (workstream SEC-GAMING, 2026-09-02)

**Status:** accepted 2026-09-02, `code/1080_sec_gaming_facility_revenue.py`.
File ownership declared here, per AGENTS.md *Parallel agents*. Nothing was
committed.

### The decision

Gaming already fences a **regulator's** figure off from an **operator's
self-published** claim. A figure a public company filed with the SEC about a
tribal casino is **neither**, and it does not go in either bucket.

* It is **stronger** than a marketing page: filed under a federal disclosure
  obligation, and in a 10-K it sits inside or beside audited statements.
* It is **different in kind** from an NIGC figure: it is the filer's own
  accounting of its own contract or its own property, not a regulator's
  measurement of the industry.

So it gets `assertion_class = SEC_FILED_FINANCIAL_DISCLOSURE` (and
`SEC_FILED_CONTRACT_TERM` for the no-money terms table), both deliberately
outside `cedar_domain.MeasurementType` and outside the `SELF_PUBLISHED_*`
family, with `not_summable_with` populated on every row.

**The specific double-count this prevents:** an SEC-derived property revenue
summed against an NIGC `REGIONAL_GGR_CEILING`. The property is inside the
region and the ceiling already contains it. `1080 verify` V13 measures the
overlap instead of asserting it away: 7 of the 8 facilities here also carry a
regional-ceiling bound row.

**A second decision, forced by the evidence:** a management fee does NOT imply
revenue. IGRA's "net revenues" (25 U.S.C. 2703(9)) is nearer operating profit,
and the contracts in this corpus variously use *net revenue as defined*, *net
income as defined*, a *threshold*, and a *floor*. Inverting a fee recovers the
contract's own base, so derived figures are typed
`DERIVED_FACILITY_*_AS_DEFINED` and V10 exits 1 if a derived figure wears a
reported figure's type. Two of eight formulas were invertible; six were refused.

### Files this workstream owns for the duration of the pass

| file | what is written | how |
|---|---|---|
| `data/clean/sec_gaming_financial_disclosures.csv` | **new file**, 67 rows | `code/1080 build` |
| `data/clean/sec_gaming_management_contract_terms.csv` | **new file**, 7 rows | `code/1080 build` |
| `review/sec_gaming_1080_candidates.csv` | **new file**, 123 mined candidates | `code/1080 mine` |
| `review/sec_gaming_1080_adjudication.csv` | **new file**, 143 hand rulings | `code/_1080_adjudication.py` |
| `code/1080_sec_gaming_facility_revenue.py`, `code/_1080_facility_aliases.py`, `code/_1080_adjudication.py` | **new** | - |
| `docs/SEC_GAMING_FACILITY_REVENUE_BUILD_LOG.md` | **new** | - |
| `docs/MONEY_TOTALLING_RULES.md` | **append only, inside `<!-- BEGIN SEC-GAMING -->`** | no other block touched |
| `docs/methodology/gaming.md` | **one new section inside `<!-- BEGIN SEC-GAMING -->`, plus one added paragraph under "The thing a reader has to accept"** cross-referencing it. The headline claim itself is unchanged. Backup: `.bak_2026-09-02_pre_1080_sec_gaming_facility_revenue` | this file has no marker convention today; markers were used anyway |
| `code/512_build_dataset_contracts.py` | **`GRAIN_SEC_GAMING` added; no other workstream's dict touched.** Backup: `.bak_2026-09-02_pre_1080_sec_gaming_facility_revenue` | per AGENT_FIELD_GUIDE section 2 |
| `code/500_build_architecture_map.py` | **one token, `sec_gaming_`, added to the `gaming` collection's table regex.** Without it both tables are orphan shippables, because they deliberately do NOT wear the `gaming_` prefix - the different prefix is the different assertion class. Backup: `.bak_2026-09-02_pre_1080_sec_gaming_facility_revenue` | additive; cannot dislodge another table |
| `data/clean/codebook/07zq_*.csv`, `07zr_*.csv` | **two new codebook fragments.** `codebook_master.csv` NOT touched - folding fragments into the master is `cedar_codebook.py build`, which is the integrator's call because it folds every agent's in-flight fragment at once. **Until that runs, both tables count against `tables_undocumented_in_codebook` in gate 62.** Keys were checked against both the fragment directory and the master's `dataset` column; `07p`/`07q` were taken and a first attempt at them was deleted before any build saw it | `code/1080 codebook`, which now refuses a key documenting a different table |
| `START_HERE.md` | **one row added to the per-dataset index table**, in the gaming block | single-line insert |

**Not touched:** `data/clean/gaming_facilities.csv`, `gaming_revenue_bounds.csv`,
and every self-published gaming table. Nothing was written in place anywhere in
the gaming universe; both outputs are new files beside it.

**Not ours:** municipal continuing disclosure. Tribal gaming authorities with
public debt file property-level operating data on EMMA, which is a parallel
route to the same figure and belongs to the tribal-debt workstream. This pass
stopped at the SEC boundary on purpose.
<!-- END ADR-SEC-GAMING -->

<!-- BEGIN ADR-025-STALE-TAIL-1081 -->
## ADR-025 — the stale-entity tail acquisition (workstream STALE-TAIL, 2026-09-02)

**Status:** accepted 2026-09-02. Declared per AGENTS.md *Parallel agents*.

**Files this workstream owns**

| file | what is written | script |
|---|---|---|
| `code/1081_stale_tail_dated_facts.py` | the acquisition, its `verify` and its `selftest` | — |
| `data/clean/entity_dated_public_facts.csv` | **new table.** One row per (entity, route, source, fact_key, identifier). Nothing else writes it. | `code/1081_*` |
| `docs/STALE_TAIL_CLOSURE_1081.md` | **new doc.** The before/after and the honest negatives | `code/1081_*` |
| `data/staging/stale_tail_1081/` | the CCD year cache and the ProPublica payload cache | `code/1081_*` |

**Regenerated, not hand-edited:** `data/clean/cedar_entity_freshness.csv` and
`docs/ENTITY_FRESHNESS.md` are 830's output and were refreshed by re-running
`code/830_entity_freshness.py`, which is the documented way. Backed up first to
`.bak_2026-09-02_pre_1081_stale_tail_dated_facts`.

**Explicit non-overlap with the two live sibling workstreams.**
`code/1020_tail_web_probe.py` owns the WEB tail (does an entity have a site);
`code/1021_register_only_first_rows.py` owns the register-only slice's FIRST
ROW, in `data/staging/`. This workstream writes no website, mints nothing, and
its slice is the 830 freshness tail — a different population and a different
question. It **imports** 1021's name-matching rather than copying it, so the
school-level conflict refusal, the all-generic fallback and the Navaho/Navajo
substitution tolerance cannot drift into two versions.

**A UEI, an EIN and an NCES id are LOOKUP KEYS here, never links.** No tier is
inherited. The ledger contributes only `confidence_tier == A` rows with an
empty `exclusion_id`; every EIN is re-verified against the IRS's own name for
it before a date is written; a name that fails is kept as `NOT_MATCHED` with
what was seen.
<!-- END ADR-025-STALE-TAIL-1081 -->

<!-- BEGIN ADR-026-RULING-PROPAGATION -->
## ADR-026 — a superseded figure gets a GATE, not a fix

*2026-09-02. Owner: the ruling-propagation pass. Script:
`code/1116_ruling_propagation_2026_09_02.py`. No commits.*

### The decision

**When a measured correction supersedes a figure, do three things and in this
order: derive the replacement from the live files, answer the old literal
wherever it stands, and leave behind a check that fails while any of them is
unanswered.** Correcting the documents alone is not enough, because the corrected
number rots exactly the way the number it replaced did.

`1116` implements that. `derive` re-derives the whole 2026-09-02 correction set
from `data/clean/` and `review/` and prints the *sentence*, so a writer pastes a
measurement rather than a memory. `verify` scans all `.md` under `docs/` and
`review/` for the superseded literals and **exits 1** while any stands with
nothing beside it. `selftest` proves the scanner fires on a poisoned fixture, is
quiet on a marked one, and reports **UNMEASURED rather than clean** when the doc
walk matches nothing.

That last point is the reason the script exists in this shape. `1111` proved
rows and dollars conserved to the cent on a table in which it had attributed
nothing: **conservation was never the risk.** A check that can only pass is not
a check, so `1116 verify` was written to fail on the state the work was supposed
to remove, and the fixture proves it does.

### Two scoping rules the gate needed, and why

* **Doc-level vs neighbourhood.** A shared **denominator** is answered by one
  note per document (`GAMING-DENOMINATOR-2026-09-02`), because a reader needs
  the denominator once, and nine near-identical banners is how a document stops
  being read. A wrong **noun** — `787 facilities` where 787 is a row count — is
  a local defect and still fires wherever the note is not in view. Both
  behaviours are asserted in `selftest`.
* **Strike, never delete.** A literal is ANSWERED by `~~...~~` or by a
  supersession marker within 1,400 characters. The old number stays visible,
  because a reader who meets it in a third document needs somewhere to find out
  it is dead. This is the discipline `START_HERE.md` already applies to its own
  corrections and it is why they are arguable rather than silent.

### Marker discipline: what this pass did to other workstreams' blocks

`docs/MONEY_TOTALLING_RULES.md` is written wholesale by
`code/574_ws1_money_and_conservation.py`, which preserves only marked blocks.
Four superseded figures in it sit inside `INT-READY`, `SEC-GAMING` and
`GAMING-DEEP` — three other workstreams' blocks.

**No block was rewritten.** A new block,
`<!-- BEGIN GAMING-DENOMINATOR-2026-09-02 -->`, was appended at the foot of the
file carrying the derived denominator and the sealed-revenue disposition; inside
the three existing blocks, a **single attributed correction line** was appended
beside each superseded figure, marked *"correction appended from outside this
block"*, with the surrounding prose left exactly as its author wrote it. The
same was done to the `TERMS-SCOPE` block in `docs/PUBLICATION_POLICY.md`, whose
eight-source bullet the owner superseded the same day.

**The rule this asserts:** the marker convention forbids *destroying* another
agent's work, not *annotating* it. An append that is signed, dated and reversible
is how a correction reaches a block you do not own. Rewriting the block is not.

### The pass corrected itself once, and that is the most useful thing in it

`1116`'s first `d_gaming_denominator()` tested `facility_name == "no casino"`,
found **7** placeholders, and derived **734** — which it then wrote as an
authoritative note into fourteen documents. **734 is one of the five partial
denominators the integrator had pinned in `be17bdb` the same evening**, and the
gated ladder in `code/846_session_audit.py::_denom` is 787 rows − **16** names
that say no casino = 771 facility rows − 57 duplicate extras = **714 distinct
properties**. Nine rows say *no casino* inside a longer name and an exact-string
test cannot see them.

So the script written to stop superseded numbers propagating propagated one, to
fourteen documents, inside an hour. All fourteen were rewritten from the gated
ladder; `1116` now **reproduces 846's algorithm and refuses** — prints
UNMEASURED, exits 1 — if the two disagree, rather than publishing a second
answer. Two detectors for one class drift, and a drifted detector is worse than
none because it is trusted; that is why `248` is a retired stub pointing at
`293`, and the same reasoning applies to a derivation.

**Two rules out of it, both now in `docs/AGENT_FIELD_GUIDE.md` §3:** an
exact-string test on a free-text column measures the string, not the fact; and
where a gated authority for a number already exists, follow it and assert
agreement — do not derive a rival.

### What is now gated

`787` (a row count read as a facility count), `174 facilities`/`174 sealed` (the
count of an assertion read as the count of its evidence), `2,142` and `$38.19B`
(one join leg of three), `1,195` (a channel count read as a corpus), and
`excluded by every route` (superseded by the owner's terms ruling). Add to
`SUPERSEDED` in `1116` when the next figure moves; the list is the record.

### Related

ADR-016 (`526`: an instruction may not be issued from a sample) ·
ADR-019-QUARANTINE (the three join legs) ·
ADR-025-STALE-TAIL-1081 (`830`, the self-referencing instrument) ·
`docs/AGENT_FIELD_GUIDE.md` §3, whose fifteen instances became twenty-four and
whose four habits became fifteen rules in this pass.
<!-- END ADR-026-RULING-PROPAGATION -->

<!-- BEGIN ADR-027-CORROBORATION -->
## ADR-027 — the corroboration layer: an evidence FAMILY is a class of observer (workstream CORROBORATION, 2026-09-02)

**Status:** accepted 2026-09-02. Declared per AGENTS.md *Parallel agents*.

**Decision.** Corroboration is counted in **independent evidence families**,
where a family is a class of OBSERVER — not a file, a row, a URL or a source
id. Three rules make the count un-inflatable, and all three are enforced by
`verify`:

- **R-A** one upstream document is one observation. `web.archive.org/web/<ts>/<url>`
  normalises to `<url>`; it is that page, not a second witness.
- **R-B** one publisher is one observer where the family is also equal.
- **R-C** a family PAIR collapses when the two share an upstream *for this
  predicate*. `federal_registry` + `federal_transactional` are ONE family for a
  legal name (USAspending copies SAM) and TWO for an identifier binding (DLA
  issues the CAGE, SAM.gov the UEI, FPDS records the binding used on an award).
  **Predicate-scoping is the part the source registry's global `derives_from`
  tree cannot express**, and it is what earns 76 of the 320 corroborations.

**Three families do not vote and are named rather than dropped**, so the
exposure stays countable: `cedar_inference` (a name match, a containment link,
`cluster_v3`, a resolver output — Cedar agreeing with itself),
`compiled_directory` (Casino City Press, legacy CICD, a vendor property list —
the same ruling `cedar_source_registry.csv` already applies to `LR_CICD`), and
`unattributed`. An eighth voting family, `third_party_press`, was added because
the seven in the mandate had nowhere honest to put a trade journal.

**Files this workstream owns**

| file | what is written | script |
|---|---|---|
| `code/1118_corroboration_layer.py` | the layer, its 8 invariants and its selftest | — |
| `data/clean/cedar_corroboration_observations.csv` | **new.** One row per observation, with family, upstream key and quote | `code/1118_*` |
| `data/clean/cedar_fact_corroboration.csv` | **new.** One row per fact, with `n_independent_families` | `code/1118_*` |
| `data/clean/cedar_corroboration_disagreements.csv` | **new.** Both sides, both quoted, never reconciled | `code/1118_*` |
| `data/clean/cedar_corroboration_census.csv` | **new.** Per shipping dataset, reason never blank | `code/1118_*` |
| `data/clean/cedar_corroboration_conservation.csv` | **new.** `rows_in == sum(named dispositions)` | `code/1118_*` |
| `docs/CORROBORATION_LAYER_2026-09-02.md` | **new doc.** The measurement, the disagreements and the merge proposals | — |

All five tables are **INTERNAL**. They measure Cedar's evidence base rather
than describing Indian Country, and the disagreement table names organisations
against claims nobody has adjudicated.

**Explicit non-overlap.** `code/510_assertions.py` owns entity-grade facts and
its own numbers are unchanged; this layer measures the SHIPPING datasets one
level out and **the two counts must never be added together**.
`code/503_identity.py` and `docs/ENTITY_MATCH_RULES.md` own whether two names
are one entity — untouched. Nothing in `nest_enterprises.csv`,
`deals_classified.csv`, `np_orgs.csv`, `gaming_facilities.csv` or
`cedar_identifier_ledger_final.csv` was edited; five merge proposals are in the
doc, each naming its owner.

**What it measured.** 320 of 4,432 facts (7.2%) reach two or more independent
families; 1,399 reach none. Nine of the fourteen shipping datasets are wholly
single-sourced, and the census distinguishes
`SINGLE_FAMILY_BY_CONSTRUCTION` (the source IS the fact) from
`NOT_REACHED_BY_THIS_PASS` (a real pair exists and nobody built it) — only the
second is a task.
<!-- END ADR-027-CORROBORATION -->

<!-- BEGIN ADR-028-ACQUIRE-1119-1121 -->
## ADR-028 — three new sources, and the four decisions they forced (2026-09-02)

**Status:** adopted for the acquisition; **three items below need the
integrator or the owner and are marked so.**

**Workstream `ACQUIRE-1119-1121`.** Owns, and edited: `code/cedar_arcgis.py`
(new shared client), `code/1119_acquire_biamaps_arcgis.py`,
`code/1120_acquire_usac_open_data.py`,
`code/1121_acquire_nppes_corroboration.py`, the `GRAIN_ACQUIRE` dict in
`code/512_build_dataset_contracts.py`, three new codebook fragments, the
`<!-- BEGIN ACQUIRE-BIA-ACREAGE -->` block in `docs/MONEY_TOTALLING_RULES.md`,
two comment-and-pattern additions in `code/500_build_architecture_map.py`, and
`docs/BIAMAPS_ACQUISITION_LOG_2026-09-02.md`.

**Did NOT touch:** `code/510_assertions.py`, `503`, `62`, `517`, `518`,
`build.py`, or any table another workstream writes. Nothing was committed.
The pass-3 ownership table says *"Integrator owns 62, 512, 517, 518"*; the
`512` edit is the one documented exception — `1050_preflight.py shared` and
`docs/AGENT_FIELD_GUIDE.md` §2 both instruct a workstream to add **its own
`GRAIN_*` dict** to that file and touch nobody else's, which is what was done.

### D1 — a new shared client rather than a fourth copy of the same five checks

`code/cedar_arcgis.py`. Three acquisitions each needed: a robots check
evaluated over **every agent token**, `robots.txt` fetched with **our own UA**,
a **sha256 per response**, an **edge-block detector that stops the run**, and a
host lock keyed by apex. Every one of those exists because this project paid
for it once — the 13 refusing hosts fetched under a naive `can_fetch`, the 22
open hosts recorded as blocked by a 403 on `robots.txt`, the `?wpdmdl=`
harvester that reported 302 documents and held one PDF, and `1085`'s four
permanent false absences written from a sub-second disconnect. Copying them
into three scripts guarantees three drifts.

`py -3 code/cedar_arcgis.py selftest` runs offline and proves each one fires,
including that the naive check MISSES a `ClaudeBot`-only rule the union check
catches, and that `reconcile()` raises on a short retrieval.

### D2 — `objectid` is the declared key, and it is non-deterministic

Four of the six ArcGIS tables have **no natural key**. On the 249,165-row
mineral acreage table, `(land_area_code, tract_id, resource_code,
ownership_type)` is 249,161 distinct, and all four collisions are real data —
three tracts with two acreages under one tract number, and one tract recorded
under two states. No published column separates the last pair.

So the key is `objectid`, which ArcGIS assigns. **That is `293`'s class 7 (a
non-deterministic primary key) and it is declared rather than hidden**, in
`GRAIN_ACQUIRE` and in both codebooks, with the rule: `retrieved_at` says
which service edition you hold, and no join on `objectid` may be persisted
across a re-pull. The alternative — inventing a synthetic hash key — would
make the instability invisible without making it go away.

### D3 — one epoch-zero sentinel, caught before it shipped

`inactivated_date` is `0` on **all 249,165** mineral acreage rows. The first
build rendered that as `1970-01-01` on every row. A filter for *"inactivated
before 2000"* would have returned the entire file, and nothing about the
output would have looked wrong. `_iso_from_epoch_ms()` now returns blank for
`0`. **A sentinel that renders as a plausible value is worse than a blank** —
the same shape as `START_HERE.md` standing rule 1b, where a populated cell was
read as a resolved identity.

### D4 — the NPPES query passes the NAME and nothing else

> **This is the decision that makes 1121 a corroboration rather than an echo,
> and it cost match rate on purpose.**

The NPPES API accepts `state=` and `city=`. Sending Cedar's own `state` would
have raised the apparent hit rate and made the result worthless: a search
seeded with our answer can only return records that agree with it.
`docs/ASSERTION_LAYER.md`'s evidence-lineage rule — *a copy of a source in the
spine and the source itself are the same evidence family* — applies to a query
parameter exactly as it applies to a table.

Consequence, and it is the point: **`state_agrees = DISAGREE` is a reachable
value**, and `1121 verify` **fails if the file contains zero DISAGREE rows**.
A corroboration source that can only ever agree is measuring itself, and a
green check on such a file is the strongest thing that check can say while
meaning nothing.

### ⚠ I1 — INTEGRATOR: three `source_id` values are not in the source registry

The new tables carry `source_id` values `bia_biamaps_arcgis`,
`usac_open_data` and `cms_nppes`. **None is in
`data/spine/cedar_source_registry.csv`** (17 rows), and that file is
**generated by `code/510_assertions.py`**, which this workstream does not own
and did not touch. The rows are therefore *proposed*, with their lineage
reasoning, in `docs/BIAMAPS_ACQUISITION_LOG_2026-09-02.md` §"Source registry
rows to add". The one that matters is the lineage:

* `bia_biamaps_arcgis` — **`LR_BIA_DIRECTORY`, `derives_from
  LR_FEDERAL_REGISTER`, `tier_ceiling B`.** It is the same evidence family as
  the existing `bia_directory` entry. Agreeing with the FR about *which
  nations exist* is an echo. It is genuinely new for `entity.bia_region`,
  `entity.bia_agency` and the PL 102-477 dates, and **`bia_ofa_petitioners` is
  a negative case the FR family structurally cannot produce.**
* `usac_open_data` — **a new root, `LR_USAC`, `tier_ceiling A` for
  `entity.tribal_school_type`.** FCC universal service is unrelated to
  Interior, Treasury or SAM.
* `cms_nppes` — **a new root, `LR_CMS_NPPES`, `tier_ceiling A` for a health
  organisation's registered address.** This is the third evidence family
  `START_HERE.md` item 0 asks for.

### ⚠ I2 — INTEGRATOR/OWNER: ADR-013 has no basis for a denominator table

`usac_rhc_hcp_directory.csv` is the **full** 11,142-provider RHC universe,
held so the 5,109-row Native candidate slice has something to be divided by.
**Most of its rows are not Indian Country and are not meant to be.** None of
C12's six adopted bases (`named_entity`, `term_match`, `program_authority`,
`geographic`, `subject_classification`, `human_ruling`) is true of it, and
picking the nearest fit would make a non-Native table claim a Native basis.

It is written as `inclusion_basis = NOT_INDIAN_COUNTRY_SCOPED_DENOMINATOR`, a
value **proposed, not adopted**. The general question is worth answering once:
Cedar's coverage percentages need denominators, and a denominator is by
construction wider than the scope. Either C12 gains a seventh value or such
tables are held outside the shippable set — but they must not silently claim a
basis they do not have.

### ⚠ I3 — OWNER: BIE schools was not `NOT_ACQUIRED`, and the survey says it was

`docs/SOURCE_EXPLORATION_2026-09-02.md` rates *"BIE Schools Directory — 183
schools"* **ACQUIRE**, second by priority. It is already on this machine:
`data/raw/external/bie_uio/bie_schools_featureserver.json`, **187 features**,
fetched 2026-08-06 by `code/75_add_bie_schools_and_uios.py` from
`services1.arcgis.com/UxqqIfhng71wUT9x`, and re-fetched 2026-09-01 into
`data/staging/tribe_harvest/shard_g/`. The state is
**`ON_DISK_NOT_PROMOTED`**, not `NOT_ACQUIRED`.

The field guide already names this class: *"27 of the 39 ranked absences are
`ON_DISK_NOT_PROMOTED`"* and *"at least three sessions have re-downloaded
files that were already on this machine."* **The survey did not run
`py -3 code/1050_preflight.py ondisk` on its own ACQUIRE list.** One command
per candidate would have caught it. Recommend that `1111`'s `report` call
`ondisk` for every row it is about to rate ACQUIRE, so a survey cannot rate a
fetch that has already happened.
<!-- END ADR-028-ACQUIRE-1119-1121 -->

<!-- BEGIN ADR-029-DEFECT-SWEEP -->
## ADR-029 — the defect classes are swept RETROACTIVELY, and the sweep is one file (workstream DEFECT-SWEEP, 2026-09-02)

**Decision.** `code/1115_defect_class_retro_sweep.py` is the single retroactive
sweep for the named defect classes across **all** of `code/` and **all** of
`data/clean` + `data/spine`. It does not duplicate an existing detector: class
12 (marker names) reuses `845.MARKER_RE`, class 13 (positional writers)
reports `845.collect_csv()` verbatim, and classes 1/2b/3/5/6/7 of `293` are
untouched. **Two detectors for one class drift, and a drifted detector is
worse than none** — the rule that retired `248`.

**Why a new file rather than more of `293`.** `293` is a per-line AST linter
over `code/` with a baseline ratchet consumed by `62`. Half of these classes
are only visible in the **data** — a sentinel string, a broken functional
dependency between a display column and a keying column, a token-match method
keying a dollar. Putting a 10.5-million-row full-table pass inside the lint
entry point would make `62` a five-minute gate.

**File ownership taken this pass.** Only these, and each is the *named
canonical instance* of its class rather than a sweep of everything found:

| file | change | proof |
|---|---|---|
| `code/526_dataset_standard.py` | `scan(name, cap=20000)` → `cap=None`. The cap was a DEFAULT ARGUMENT, invisible at the call site, and `build()` recommended `drop N always-empty column(s)` on 20,000 rows of 1.2M-row tables | full pass over all 363 tables = 115 s, measured. Sibling `518` had already set `SCAN_CAP = None`. **Not run** — its output is another agent's input |
| `code/1111_copper_river_attribution.py` | `verify` refuses below a 1,000-row floor instead of passing on an empty target set | re-run live: `ok  4,272 Copper River rows, 0 not on the hub`, exit 0 |
| `docs/KNOWN_ISSUES.md` | new block `DEFECT-SWEEP-1115` only | — |
| `review/OWNER_DECISION_QUEUE.md` | new block `DEFECT-SWEEP-1115-QUEUE` only (DS-1, DS-2) | — |
| `docs/ARCHITECTURE_DECISIONS.md` | this block only | — |

`docs/defect_class_retro_sweep.json` is generated; do not hand-edit.
**`62`, `512`, `517` and `518` were not touched.** No commit.

**PROPOSAL TO THE INTEGRATOR — rule 18, beside rule 17.** Rule 17 makes the
regenerate defect permanent by importing `845`. Nothing yet makes the other
twelve permanent. `1115` exposes `run_code()` and a per-class count in
`docs/defect_class_retro_sweep.json`; the code half runs in **42 s** and opens
no socket. The recommendation is deliberately narrow:

- ratchet the **code-half** counts (C1, C2, C3, C5, C8, C9, C12, C12b) as
  MUST_NOT_RISE, the same arrangement as `293`;
- do **not** ratchet the data half from inside `62` — it is a 115-second full
  pass and belongs on a cadence, not on every gate run;
- import must follow rule 17's own discipline: a failure to import or to scan
  is **UNMEASURED**, never zero. `1115` already emits `UNMEASURED` entries and
  `all` runs its 11 fixtures first and says so if any failed.

**What is deliberately NOT claimed.** Classes **C10** (a decision written
where the asker cannot see) and **C11** (a present-tense map inverting a past
event) have no detector and no number. Neither is derivable from code shape or
column shape, and a count that pretended otherwise would be exactly the defect
this repo is named for — a check that measured something other than its own
name. They are recorded in the report under `not_mechanically_detectable` so
the next reader does not mistake their absence for a clean result.
<!-- END ADR-029-DEFECT-SWEEP -->

<!-- BEGIN ADR-027-CAPABILITY-1114 -->
## ADR-027 — the capability-statement harvest owns nothing in `data/clean/`

*2026-09-02. Owner: the capability-statement pass. Script:
`code/1114_capability_statement_harvest.py`. Build log:
`docs/CAPABILITY_STATEMENT_HARVEST_2026-09-02.md`. No commits.*

### Files this workstream owns, in full

| path | what is written |
|---|---|
| `code/1114_capability_statement_harvest.py` | the acquisition, its `purge`, its `verify` and its `selftest` |
| `data/staging/capability_1114/*` | worklist, host probe log, document log, surfaces, findings, coverage, refusals, purge record, run summary |
| `review/capability_statement_identifiers_1114_2026-09-02.csv` | the 145 distinct identifiers, one exhibit each |
| `docs/CAPABILITY_STATEMENT_HARVEST_2026-09-02.md` | this pass's build log |

**It writes NOTHING in `data/clean/` and rebuilds no shared table.** In
particular it does not touch `cedar_identifier_ledger_final.csv`,
`cedar_harvest_coverage_matrix.csv` or `cedar_harvest_coverage_evidence.csv` —
the coverage matrix is `code/1112`'s and re-running 1112 is how its cells move.
`data/staging/capability_1114/coverage_1114.csv` is a **parallel** measurement in
1112's own six-value vocabulary, joinable on `cedar_uid` + `harvest_type`, and
the integrator decides whether it merges.

### The decision: a second source is only a second source if it is a different family

The 53 corroborations this pass produced are worth having **only because the
entity's own page and FPDS are different evidence families**. That is a design
constraint, not a description, and it is enforced in the worklist rather than
trusted: `THIRD_PARTY_TYPES` and `THIRD_PARTY_HOSTS` exclude ProPublica,
`web.archive.org`, IRS, SAM, USAspending, GuideStar, `bia.gov`, `nigc.gov` and
Wikipedia from ever being selected as "the entity's site". The first cut of the
worklist did select them — `projects.propublica.org` was a "host" for several
entities — and every identifier read there would have booked a corroboration
that does not exist. `docs/ASSERTION_LAYER.md` already says a copy of a source
is the same source; this is that rule made operational in a selection step.

### Two conventions this pass adds, both narrow

* **A released host is probed as itself.** The run dedupes on
  **(cedar_uid, host)**, not on cedar_uid, because one entity can legitimately
  have both a government site and a released host the ruling names by name.
  Deduping on the entity skipped `colvilletribes.com` and `ctuir.org`.
* **A publisher-stated host is exempt from the name check, and records that it
  was.** The circular-evidence rule in `docs/HIDDEN_DATA_TECHNIQUES.md` is about
  *guessed* domains. `nana.com` carries no class marker on its homepage and
  gating on that would have recorded the released host as "not the entity". The
  verdict is still written to the row, tagged `NOT GATED`, so a later gate can
  read back exactly which rows were exempted and why.

### Marker discipline

This pass added `<!-- BEGIN CAPABILITY-1114 -->` to `docs/KNOWN_ISSUES.md` and
this block to `docs/ARCHITECTURE_DECISIONS.md`, and appended one item to
`review/OWNER_DECISION_QUEUE.md`. It edited no other workstream's block, added
no `GRAIN_*` dict to `code/512`, and touched neither `62` nor `518`.
<!-- END ADR-027-CAPABILITY-1114 -->

<!-- BEGIN ADR-030-PLACE-IDS -->
## ADR-030 — ONE Cedar identifier for PLACES, and the candidates that were refused

*Decided 2026-09-02. Built by `code/1129_place_ids.py`. Register:
`data/spine/cedar_place_id_register.csv`. Directory: `data/clean/cedar_places.csv`.
Gate: `py -3 code/1129_place_ids.py verify` (15 checks) and `selftest`, which
proves four of them FIRE.*

### The owner's question, and the test that answers it

> *"we probably need IDs for other things. Right? Like gaming properties so we
> can know we're talking about the same property... what things need IDs and
> what would be easy to track. I don't want a billion IDs, obviously."*

> *"We need our own ID system for certain things. Like, casinos make sense.
> Enterprises in general makes sense, so you can analyze — **it's like our own
> D-U-N-S number**, basically."*

**THE TEST.** A thing earns a Cedar identifier only when all three hold:

1. it **recurs across two or more sources that key it differently**, AND
2. **Cedar must assert** that two records are the same thing, AND
3. **no stable external identifier already exists.**

**THE D-U-N-S ANALOGY IS THE DESIGN SPEC.** A D-U-N-S names an *operating unit*
and survives a rename, an ownership change and a relocation, because it names
the thing rather than the current facts about it. That is exactly the property
a Cedar place id must have, and it is the whole reason one is worth minting. A
casino that is renamed, transferred to a different tribal enterprise and rebuilt
across the road is the same place; an id that has to be reissued for any of
those is not an identity, it is a label.

### THE DECISION: one `CEDAR-PLACE` id, four classes, class in a COLUMN

```
CEDAR-PLACE-000123-K7
|           |      \- two check characters, from two independent weightings
|           |         (503_identity.check_chars - one linear, one quadratic, so
|           |         an error in the null space of one is caught by the other)
|           \- 6-digit ordinal, allocated by cedar_ids.allocate() under an
|              exclusive file lock, so two agents cannot mint the same id
\- namespace: what KIND of thing this id names
```

`place_class` is one of `GAMING_PROPERTY`, `BIE_SCHOOL`, `IHS_FACILITY`,
`BIA_OFFICE`. **The class is a column, never the prefix.** `cedar_ids.id_type()`
reads the registry and never infers from a string — for the same reason
`cedar_uid` encodes nothing (`IDENTIFIER_STANDARD.md` §0): a gaming property
that stops gaming must not have to be re-keyed, and rewriting an identity is
the one unforgivable act in an identity system.

**The contract, copied from `503` and enforced rather than described:**

| promise | how it is held |
|---|---|
| permanent | the binding `(place_class, source_scheme, source_key) -> id` is read FIRST, always |
| never reused | a closed casino keeps its id; ordinals only ever go up |
| check-digited | `503_identity.check_chars`. `O`, `I`, `L`, `U` are not in the alphabet, so the zero-for-O error is *unrepresentable*, not merely detectable |
| minted once | the register is APPEND-ONLY. **Proven: a second `mint --apply` minted 0 and reproduced 1,051 identical bindings.** |
| a sub-hub | a place hangs off the entity that OPERATES it, never a peer of it, and **the operator can change without the place changing** |

**One check-character implementation in the project.** `1129` renders the
ordinal `cedar_ids` allocates and appends `503`'s two characters — the same
split NEST uses for `CEDAR-NEST-nnnnnn-CC`. Allocation is permanent and locked
in one place; transcription safety comes from another; neither is
re-implemented.

**"Queued per dataset" is namespacing, not separate registers.** One atomic
allocator (`cedar_ids._Lock`, `O_CREAT|O_EXCL`), one prefix per kind of thing:
`CE-` entities, `CEDAR-NEST-` enterprises, `CEDAR-PLACE-` places. Two datasets
cannot collide because they share the allocator, not because they avoid each
other.

### WHY A PLACE PASSES THE TEST — the evidence, not the argument

**1. Recurs across sources keyed differently.** `gaming_facilities.facility_id`
is *source-scoped*: **595 `CCP-` (Casino City Press), 164 `VP-` (a second
vintage), 15 `TPL-`, 13 `CED-`**, and **26 clean tables key on it** — 24 with at
least one non-blank value, two declaring the column and never populating it.

**2. Cedar must assert two records are the same thing.** That split is *why*
there are 58 same-name candidate groups. `Casino Del Sol` (`CCP-544900`) and
`Casino Del Sol Resort` (`VP-0041`) are one property at 5655 W Valencia, Tucson,
held twice, and 26 tables inherit the split.

**3. No stable external identifier exists — and the one that looks stable
collides.** `bia_offices.OFFICEID` is **not unique**: `OFID0038` is *both*
**Salt River Agency** (33.4662, -111.8655) and **San Carlos Agency** (33.3537,
-110.4528), two agencies 130 km apart. 93 rows, 92 ids. An external identifier
that collides is not one — and that is exactly what the mint fixes: after
migration those two rows carry two distinct `cedar_place_id`s, and `OFFICEID`
is kept beside them as evidence of where the row came from.

### THE CANDIDATES THAT FAIL THE TEST — named, so nobody re-opens them

| candidate | fails on | why |
|---|---|---|
| **Federal awards and contracts** | **3** | PIID and UEI are stable, federally assigned, and already the join key. A Cedar id here would be a second name for something that already has one. |
| **Federal Register and NAGPRA documents** | **3** | the FR document number and the NAGPRA notice id are stable federal identifiers. `federal_actions.csv` and `nagpra_notices.csv` — the two datasets already READY — key on them today. |
| **Geographies** | **3** | FIPS and GEOID are stable, versioned and universally understood. Minting over them would make Cedar's geography unjoinable to every other dataset in the world. |
| **Enterprises** | **already minted** | `CEDAR-NEST-nnnnnn-CC`, 1,610 bindings in `data/spine/cedar_nest_id_register.csv`. The owner's *"enterprises in general makes sense"* is **already satisfied**. A second enterprise id is the "billion IDs" failure in its purest form. |
| **Deals** | **already minted** | `deals_classified.Deal_ID` is Cedar-minted. See EVENTS below — it needs GENERALISING, not a sibling. |
| **People** | **policy, not a test outcome** | never, for any reason. A natural person's data held apart from their public role is `CONSTRAINED`, and a person-level identifier is precisely the artefact that would make re-identification cheap. |

### EVENTS / TRANSACTIONS — passes the test, and the answer is to GENERALISE `Deal_ID`, not to mint beside it

Tested honestly rather than assumed, and it **passes all three**:

1. *Recurs across sources keyed differently* — **yes.** The Bristol Bay
   Industrial / GHEMM acquisition of 2022-06-15 is held twice: once from the
   ANCSA portal as `ANCSA2-2022-003`, and once found independently in EDGAR.
2. *Cedar must assert two records are the same thing* — **yes, and it is already
   doing it by hand.** The deals merge refused 36 internal duplicates across
   four staging channels and found 17 candidates already in the ledger.
3. *No stable external id exists* — **yes.** An SEC accession number identifies
   a **filing**; a PIID identifies an **award**. Neither survives the same
   transaction being reported in two places, which is the whole problem.

**And `Deal_ID` carries the same defect `facility_id` does: it is
SOURCE-SCOPED.** Measured on the live table — 1,073 rows, 15 channel prefixes:
`FA-NTI` 272, `FA-HUD` 222, `ND-202…` 154, `NLTR-2…` 90, `FA-EDA` 51,
`FA-DOE` 49, `ANCSA2` 42, `ANCSA-` 34, `ANCSA3` 24, `SECX-2` 22, `MA2020` 14,
`ACQ202` 8, `IDOBS-` 2. The prefix records **which pipeline found the event** —
exactly what `CCP-` and `VP-` record — and it will split the same event the
same way.

**RECOMMENDED, NOT DONE TONIGHT, and deliberately so.** The mandate was to mint
**one** id and only one; minting a second in the same pass is the thing the
owner said he does not want. The proposal is a **generalisation**: keep
`Deal_ID` on every row as the source key — it is the evidence of which channel
found the event — and mint a `CEDAR-EVENT-nnnnnn-CC` beside it that also covers
ownership changes visible only in contracting and never reported as a deal.
One concept, one id, one register: the same shape as this ADR. It is an owner
decision because, like the 58 gaming groups, it will require refusing merges by
hand.

### THE ADJUDICATION — 58 groups, worked one at a time, 5 held open

`review/place_gaming_adjudication_2026-09-02.csv` carries one verdict and one
basis per group. **Three rules, ordered, each stated as a refusal so the default
is NOT to merge:**

**P0 — DIFFERENT OPERATORS: HOLD_OPEN (2 groups).** Two rows naming two
different sovereigns are not adjudicable as one place by a name test, whatever
their addresses say. `7 Clans First Council` is filed to the **Ponca Tribe**
(`VP-0170`) in one vintage and the **Otoe-Missouria** (`CCP-843900`) in the
other, at the identical street address, 12875 N Hwy 77, Newkirk OK. `The
Stables` is filed to the **Modoc Nation** (`VP-0153`) and the **Miami Tribe of
Oklahoma** (`CCP-305300`) at 530 H St SE, Miami OK — and is in fact *jointly*
owned by both. Merging either would settle an ownership question by way of a
duplicate sweep. **They stay two, and the contradiction is recorded rather than
resolved.**

**P1 — THE SOURCE ITSELF MINTED TWO PROPERTY IDS: HOLD_OPEN (3 groups).** Where
**both** rows carry a distinct non-blank `casino_city_id`, the one vendor that
mints property ids has recorded two properties, and Cedar does not overrule a
source's own property-level distinction with a name test:

- `Cities of Gold Casino` (39300) / `Cities of Gold Hotel` (841600) — a casino
  and its hotel, which the mandate names as legitimately two places;
- `Glacier Peaks Casino` (406800) / `Glacier Peaks Hotel` (1005500) — likewise;
- `Three Rivers Casino` (1126400, Coos Bay, **97420**) / `Three Rivers Casino
  Resort` (639700, Florence, **97439**) — **67 km apart**. Two different casinos
  sharing one brand. Merging these would have been a fabrication.

**P2 — otherwise: MERGE (53 groups, 54 extra rows collapse).** One operator,
names differing only in the generic facility vocabulary, two source vintages.

**THE COORDINATE PAIR IS DELIBERATELY NOT USED, and this is worth keeping.**
Measured on these groups, rows at an **identical street address** sit 519 m
apart (Seneca Niagara), 758 m (Pala) and 1,583 m (Casino Del Sol) — while the
one pair **6 m** apart (Glacier Peaks) is a casino and a hotel that are *not*
one place. The coordinates in this table are geocoded at varying precision, so
a distance threshold would have measured the geocoder, not the place. It is
this repo's signature defect in a new dress: a check that does not measure its
own name.

**16 rows are not places at all** and get **no id**, recorded in
`review/place_non_place_rows_2026-09-02.csv`. Their names *say* "no casino" —
7 exactly, 9 inside a longer name (`Grand Canyon West - no casino`, `Tribal
admin only - no casino`, `No casino currently`) — so the test is a **substring**,
never `== "no casino"`. Each is an assertion that an entity operates **no**
gaming property; it is not a record of a place, it is merged into nothing, and
`cedar_place_id_absent_reason` says so on every row that carries it. *(Three of
the sixteen incidentally name a real non-gaming place — Grand Canyon West, the
Las Vegas Paiute smoke shop, Pipe Spring National Monument. A place id for
those would have to come from a source about those places, never from a row
whose measured facts are about a casino that does not exist.)*

### THE RECONCILED COUNT: 717, and the whole difference from 714 is three named groups

`code/1129_place_ids.py::reconcile()` **computes** this ladder from the live
file on every run; `verify` check V9 fails if it stops reconciling.

```
787 rows - 16 non-places   = 771 facility rows
771 - 57 mechanical extras = 714    <- 846_session_audit.py::_denom
771 - 54 adjudicated extras = 717   <- this pass
difference = the 3 groups held by P1:
             CITIES OF GOLD (NM), GLACIER PEAKS (MT), THREE RIVERS (OR)
```

**`_denom` is not re-baselined and does not need to be.** It measures a
mechanical name-collision count and it is correct about what it measures; the
mandate staged those groups *unmerged on purpose* precisely because a mechanical
count is not an adjudication. **714 is the upper bound on merges; 717 is what
the evidence supports.** The three-row gap is the price of not merging two
casinos 67 km apart.

**Totals minted: 997 places over 1,051 source-key bindings —
GAMING_PROPERTY 717 (771 keys), BIA_OFFICE 93, BIE_SCHOOL 187.**

### IHS_FACILITY is declared and UNPOPULATED, and verify says so

There is no IHS facility directory on this machine — `1050 ondisk ihs` returns
area-office HTML and a self-governance compact list. It is **NOT_ACQUIRED**, not
`CONSTRAINED`, and not a deficiency of this pass. `verify` prints it as
UNPOPULATED and does **not** count it as a pass, because *a verify that passes
on an empty target set is the defect of the night*. The register is append-only,
so acquiring it later mints ids beside the existing ones and moves nothing.

### The sub-hub link is stated where it is blank, never guessed

- **GAMING_PROPERTY** — `operator_cedar_uid` from `gaming_facilities.cedar_uid`.
- **BIA_OFFICE** — **blank**. A BIA agency office is operated by a federal
  agency, which is not a Cedar entity; `operator_basis` says exactly that. A
  place whose operator is not a Cedar entity is still a place.
- **BIE_SCHOOL** — **blank**, with the reason on the row: 129 of 187 are
  tribally-controlled, and matching a school name to a nation by name is the
  containment defect. Blank means *unresolved*, never *no operator*. The BIE
  binding key is the normalised school name plus state — unique across all 187
  features, measured — because the feature service publishes only `OBJECTID`,
  an ArcGIS row ordinal that is not stable across a republish. That is condition
  3 of the test in its strongest form, and it is stated rather than hidden.

### Migration: 27 tables, additive, conservation proven per table

Every table **keeps its source key** and **gains `cedar_place_id` beside it**,
plus `cedar_place_id_absent_reason`, which is never blank when the id is. A
source key is the evidence of where a row came from and is never overwritten.

**194,477 rows across 27 tables · 165,212 keyed · 0 unexplained unmapped.** The
170 unmapped rows are all non-place placeholder rows, and the migration
**names every one of the 16 distinct keys** rather than tallying them — 29,095
further rows carry no source key at all and say so on the row.

Row and money conservation is **asserted inside the write** on every table: row
count identical, and **every numeric column's sum identical to the cent**,
computed before and after. An assertion failure raises; it does not warn.

### THE GATE, and the fixtures that prove it fires

`py -3 code/1129_place_ids.py verify` — **15 checks, exits 1 on breach.**
`selftest` injects four violations, asserts the **named** check fires, restores,
and re-asserts green:

| fixture | fires |
|---|---|
| **the register is emptied** | **V0** — the empty-target-set defect, tested first and on purpose |
| one transcribed check character | V1 |
| one source key bound to two ids | V2 |
| `cedar_place_id` dropped by a rebuild | V6 |

**V0 is a FLOOR per class** — `GAMING_PROPERTY >= 717`, `BIA_OFFICE >= 93`,
`BIE_SCHOOL >= 187` — so the gate goes red when the mint **did not land**, not
only when something moved (field guide rule 5). A later acquisition raises a
floor rather than breaking the gate.

### Two defects found on the way, both fixed, neither introduced by this pass

**1. `846_session_audit.py::_denom` — THE GATE FOR THIS VERY LADDER — was
measuring nothing, and had been since it was committed.** Nine **0x08 backspace
bytes** sit in the source where `\b` was intended, across three regexes in
`846`. In `_denom`'s `loose()` the pattern read `\x08(CASINO|RESORT|…)\x08`,
which matches no string that can exist, so the generic facility vocabulary was
never stripped: every name stayed distinct, the check found **0 duplicate
groups**, and it reported *"771 distinct properties — shape changed, re-derive
before quoting"*. Two other checks were blinded the same way — `\bearns\b` /
`\bawarded?\b.*\blodge\b` in the business-name detector, and
`(Tourism|Recreation|…)\b` in the NAGPRA tail detector. Confirmed present in
the committed blob (`git show HEAD:code/846_session_audit.py` counts the same
nine), so it is not a working-tree accident. **Repaired: 9 bytes, `0x08` ->
`\b`. `_denom` now PASSES at exactly 787 - 16 - 57 = 714**, which is what the
mandate said it should say. *Measured 2026-09-02: the word-boundary and
unbounded forms were compared on the live file and give identical results —
58 groups, 57 extras, 714 — so the repair changes no adjudication.*

**2. Three wholesale writers would have deleted the new column on their next
rebuild.** `1080_sec_gaming_facility_revenue.py` (`FIG_COLS`, `TERM_COLS`) and
`92_build_gaming_capacity_official.py` (`COLS`) were all flagged NEW by
`845_regenerate_guard.py` the moment the migration landed. This is class 6, and
it is the rebuild/enricher collision `START_HERE.md` records happening for the
fourth time. Fixed with the repair `845` itself prescribes and recognises
structurally: a `carry_live_columns(path, canonical)` helper that reads the live
header and returns canonical-order-first plus whatever the file already carries.
A rebuild now writes the column **blank** and the enricher refills it.
**`845 verify` is green again — 3 unsafe writers, 0 new since baseline.**

### Ordering — the enricher runs LAST

`1129 migrate` is an in-place enricher on 27 tables. A full rebuild of any of
them now preserves the column but **cannot repopulate it**. After any such
rebuild:

```
py -3 code/1129_place_ids.py migrate --apply
py -3 code/1129_place_ids.py verify
```

The `.bak_2026-09-02_pre_1129_place_ids` files beside each table are the signal
that this pass touched it.
<!-- END ADR-030-PLACE-IDS -->

<!-- BEGIN ADR-028-FORWARD-CONSTRUCTION -->
## ADR-028 — forward construction on `contractors`, `subcontracting`, `funding` (2026-09-02)

**Files this pass owns and edited.** No commit; no other workstream's marked
block was rewritten.

| file | what changed |
|---|---|
| `data/clean/prime_contracts.csv` | `1085 apply` over all nineteen archive attribute files. Four attribute columns filled on 592,925 rows. No money, entity, tier or provenance column touched. |
| `data/clean/subawards.csv` | `121 match`/`append` (+2,632), then `910 rescan`/`apply`, `911 apply`, `871`, `1109 index`/`apply`. 87,177 → 89,809. |
| `data/clean/native_passthrough.csv`, `native_passthrough_pairs.csv` | rebuilt by `81` (the declared projection) |
| `code/121_pull_subawards_api.py` | ten `geo_subawardee_*` columns registered in `POST_PROMOTION_COLS`; the "after any promotion" order corrected to include `871`, `1085 apply` and `1109` |
| `code/cedar_pipeline.py` | two `KNOWN_ORDERINGS` entries added (`121`→`1109`, `871`→`1085`). Nothing else in that file touched; `NEVER_RUN` unchanged at one entry. |
| `code/1109_*`, `code/1085_*` | `backup()` now supersedes a stale same-day snapshot, per `871`'s incident rule |
| docs | `methodology/{contractors,subcontracting,funding}.md`, `PRIME_ATTRIBUTE_REPULL_LOG_2026-09-02.md`, `SUBAWARD_API_PULL_LOG.md`, `FAADS_TRANSACTION_KEY_SETTLEMENT_2026-09-02.md`, `FAADS_ZIP_COLUMN_CENSUS.json` (regenerated), and one attributed correction inside `MONEY_TOTALLING_RULES.md`'s `DEEPEN-SUBAWARD-DENOMINATOR` block |

### The decision this pass actually makes

**A conservation proof is not a landing proof, and this repo now has three
same-day instances to prove it costs work.** `1085`'s apply, `1079`'s five
columns and `1109`'s ten all conserved every row and every cent, all reported
exit 0, and all three were absent from the live file hours later. Every one of
those checks was TRUE at the moment it ran. None of them asks the only question
that catches a revert: **is the work in the live file, now?**

So: **an in-place enricher must ship a check that fails when the work did NOT
happen, not only one that fails when something moved.** For a column promotion
that is one line — are the columns in the live header today — and it costs a
`head -1`. It is not a substitute for conservation; it is the half that was
missing.

**Second, a stale baseline makes a conservation check lie in both directions.**
`bak_<date>_pre_<stem>` embeds only the date, and `if not bak.exists()` keeps
the first run's snapshot. `871` already earned this rule; `1085` and `1109` now
carry it too. A same-day re-run supersedes a snapshot whose size does not match
the live file and re-takes it. Where a correct baseline could not be
reconstructed after the fact, `verify` prints **UNMEASURED** rather than a
number — `1109`'s INV-SGEO-1 does exactly that for the 16:58Z run.

**Third, a schema guard that blocks another workstream's landed columns must be
answered by REGISTERING them, never by deleting them.** `121 match` refused at
12:01:12Z naming `1109`'s ten columns as unfillable; by 12:03:54Z they were out
of the table. The guard was right. The resolution was not. Both `121` and
`cedar_pipeline` now know about those columns.

**Not done, deliberately.** The FAADS 112-column re-pull of the 60
FY2001–2006 agency-years is feasible and proven (see
`docs/FAADS_TRANSACTION_KEY_SETTLEMENT_2026-09-02.md`) and was **not run**: it
needs the same one-poller host that the subaward re-pull holds, and
`docs/methodology/funding.md` §4b reason 3 — that a re-pull must merge by
content or it re-points 29,594 position-keyed attributions — is an owner
decision, not an agent's.
<!-- END ADR-028-FORWARD-CONSTRUCTION -->

<!-- BEGIN ADR-031-NP-WEBSITE-AND-ANNUAL-TOTAL -->
## ADR-031 - the nonprofit website check, and publishing two money classes without a grand total

*Decided 2026-09-02. Scripts `code/1125_np_website_native_check.py`,
`code/1126_annual_total_federal_and_gaming.py`,
`code/1127_schedc_coverage_basis_fix.py`. Owner asks: "with the nonprofits, if
they have a website, check the website too" and "I think we have a more
accurate annual total of funding flowing to Indian Country when we include
NIGC's regional gaming numbers."*

**1. An organisation's own website is a genuine second evidence family; the
entity layer's web map is NOT.** `np_orgs.cedar_uid` names the entity Cedar
KEYED the nonprofit to, not the nonprofit. Reading `cedar_web_map.csv` for a
row with no 990 website field asks the Ahtna corporation's site whether AHTNA
INTERTRIBAL RESOURCE COMMISSION is Native, and a tribe's own site is Native by
construction. That route is counted (41 of the 293) and refused, never fetched.
URLs come only from a field the filer typed on its own IRS return.

**2. Silence, a land acknowledgement, serving, and being are four different
findings and get four different labels.** `CHECKED_NO_SIGNAL` is not a
refutation and says so on every row. `WEBSITE_ACKNOWLEDGES_A_NATION_BUT_DOES_
NOT_CLAIM_TO_BE_ONE` exists because the first classifier scored *"this land
acknowledgement is one small step toward true allyship"* as a Native
self-description - a sentence that names a nation in order to say the
organisation is not it. `WEBSITE_SAYS_IT_SERVES_NATIVE_PEOPLE` is kept apart
from `WEBSITE_SAYS_NATIVE` because the nonprofits methodology already refuses
to infer control from service.

**3. Verdicts are re-derived at `build` from the SAVED BYTES, never trusted
from the fetch.** Sharpening the classifier then costs no network and no host
is re-asked. It has already paid for itself once.

**4. Federal obligations and gaming revenue are published side by side and
never added.** `money_class` is `FEDERAL_OBLIGATION_TRANSFERRED_INTO_INDIAN_
COUNTRY` or `INDIAN_COUNTRY_OWN_SOURCE_REVENUE` on every row of
`annual_indian_country_money_series.csv`, no row is a grand total, and
`1126 verify` V3 fails if one ever appears. The owner is right that the annual
picture is more accurate with gaming in it; a single summed number would claim
the two are the same kind of money.

**5. `coverage_basis` is DERIVED, not stamped.** A basis is a sentence about a
row; one sentence on ten rows is a header, and a header cannot be true of every
row it sits on. Fixed at `code/99`, applied by importing 99's own function.
<!-- END ADR-031-NP-WEBSITE-AND-ANNUAL-TOTAL -->

<!-- BEGIN ADR-032-NEST-DUAL-ROLE -->
## ADR-032 — An ANC or an NHO is BOTH a register entity and an enterprise, and the second role is RECORDED, not duplicated

**Decided 2026-09-02** by workstream `nest-owner-v6`,
`code/1130_nest_owner_v6_reconcile.py`. Owner's design correction:
*"ANCs and NHOs are themselves entities, but they're also enterprises too. So
they're a unique one."*

**Context.** NEST modelled an ANCSA corporation only as an
`owner_hub_cedar_uid` — a hub that owns subsidiaries. That is half of it.
Arctic Slope Regional Corporation holds UEI `CY16XXPHX213`, is a federal
contractor in its own right and sells; so do all eight regional corporations
the owner's dataset reaches, and so do 13 NHOs registered as firms in the SBA
certification register.

**The obvious fix is wrong.** Adding the corporation to
`nest_enterprises.csv` as a row hubbed on itself breaks the dataset's key,
`(owner_hub_cedar_uid, enterprise_name_normalized)`, and makes a hub its own
subsidiary. `1072` already refuses exactly that — `The Eyak Corporation` and
`Coushatta Tribe of Louisiana` each published as a two-level chain that was
one company twice, and the build now tests the child against every
deterministic rendering of the hub's name.

**The decision.** A new one-row-per-entity table,
`data/clean/nest_entity_dual_role.csv`, keyed on `cedar_uid`.

* The register keeps ONE row for the entity. NEST keeps ZERO rows for it.
* The dual role is declared in its own table and joined to
  `nest_enterprises.csv` on `owner_hub_cedar_uid`.
* Three evidence rungs, recorded per row, never collapsed into a boolean:
  `R1_DECLARED_BY_OWNER_DATASET`, `R2_ENTITY_HOLDS_ITS_OWN_IDENTIFIER`,
  `R3_REGISTERED_AS_A_FIRM_IN_SBA_DSBS`.
* **Absence means no evidence was found, never "it does not trade."** A row
  exists only where a rung fired.
* R3 is required because the owner's own file carries exactly one NHO parent
  and therefore cannot evidence the NHO half of his own correction. R3 reads
  the SBA DSBS extract already on disk, which is a `federal_registry`
  observer rather than a restatement of his file. Uniqueness is required on
  BOTH sides — 73 register entities were refused because their own name is
  not unique in the register or in DSBS.

**Grain declared** in `code/512_build_dataset_contracts.py` as its own
`GRAIN_NEST_DUAL` dict. **Codebook** registered as
`18c_nest_entity_dual_role` (27 variables), appended to
`codebook_master.csv`, never rewritten. Invariants **I11a–I11d** and **I12**
in `1130 verify` hold the ANC reach, the NHO reach, the second evidence
family and the no-self-subsidiary line, and a fixture proves I11a fires.

**Consequence.** A consumer asking "what does this ANC own" reads
`nest_enterprises`; asking "does this ANC itself sell" reads
`nest_entity_dual_role`. Neither question is answered by a row that pretends
to be the other.
<!-- END ADR-032-NEST-DUAL-ROLE -->

<!-- BEGIN ADR-033-FAC-NONTRIBAL -->
## ADR-033 — `entity_type = tribal` is a fact about the FILING FORM, not about the filer. The FAC gets a second, disjoint table.

**Decided 2026-09-02** by workstream `FAC-NONTRIBAL-1132`,
`code/1132_fac_nontribal_native_audits.py`.

**Context.** `code/147_build_fac_single_audits.py` discovers Single Audits with
`api.fac.gov/general?entity_type=eq.tribal`. Measured on the live output:
**6,774 of 6,780 rows arrive on that net, and the table reaches 638 of the
1,555 entities in the spine.** The 917 it misses are not a random remainder —
**210 Native Hawaiian Organizations, 152 ANCSA village corporations, 115 Alaska
Native villages, 114 BIE schools, 63 state-recognized tribes, 55 Native
CDFIs**, and so on down. An NHO 501(c)(3) files as `non-profit`; a BIE school
files as `local` or `higher-ed`; a Native CDFI files as `non-profit`.
`entity_type` is the auditee's self-typing on the SF-SAC. It describes the
**form of the filing**, and Cedar was reading it as a statement about **who the
filer is**.

**Decision — a SECOND table, not a wider 147.** Two reasons, both structural.

1. **`147 --all` is a full rebuild of `fac_tribal_single_audits.csv`.** An
   in-place append into it is reverted by the next run while printing a larger
   row count — the FERC rebuild/in-place collision in `START_HERE.md`, four
   times over. A second table with its own builder is rebuild-safe on its own.
2. **A file named `tribal` may not hold 83 Native Hawaiian filings.** Loading
   them into it would be a correctness defect wearing the costume of coverage.

**The two tables are DISJOINT ON `report_id`**, asserted by invariant **V4**,
which a fixture proves fires. A row is 147's or it is 1132's, never both, so a
consumer may UNION them without double-counting a dollar.

**Consequence.** 545 further Single Audit filings on **99 entities Cedar could
not previously reach**, `$9,779,055,684` of audited federal expenditures, and
7,252 SEFA lines across 506 ALNs — an `audited_filing` evidence family
independent of FPDS and FSRS. Registered in `500`'s `nonprofits` collection and
in `512` as `GRAIN_FAC_NONTRIBAL`.
<!-- END ADR-033-FAC-NONTRIBAL -->

<!-- BEGIN ADR-034-OWNER-V6-BUILDER-INPUT -->
## ADR-034 — The owner's enterprise dataset is an INPUT to the NEST builder, not an append to its output

**Decided 2026-09-02** by workstream `NEST-OWNER-V6-INPUT-1133`,
`code/1133_nest_owner_v6_builder_input.py`.

**Context.** `1130` measured 4,786 net-new enterprises in the owner's
18,110-row v6 file and deliberately did not append them, because `1072 build`
is a full rebuild and the append would be reverted by the next run.

**Decision.** The file becomes source **7** of `1072.load_sources()`, staged as
`data/staging/nest/owner_v6_edges.jsonl` by `1133 apply`. The rows are
therefore re-derived on every rebuild, and their ids stay bound by the
append-only `cedar_nest_id_register.csv`. `1133` owns the admission decisions;
`1072` owns the clustering, the guards and the ids. Nothing is post-processed.

**Four admission decisions, each measured rather than assumed:**

* **8,927 rows whose own `attribution_method` is `unmatched` are REFUSED.**
  They are the owner's unattributed FPDS residue — `Merchen & Reed Gravel Inc`,
  `Goldenlook Of San Antonio Inc`, and natural persons (`Benward, Ursula`,
  `William Woolard`). `unmatched` is a NEGATIVE result and inheriting the row
  while dropping its sign is the 148 defect at 8,927x scale.
* **3,140 SBA-certified firms with no owner nation named are REFUSED to NEST**
  and registered for `native-owned-businesses`. NEST's grain is (owner hub,
  enterprise name); a row with no owner is not a NEST row.
* **The 160 v3-only rows are NOT recovered.** 160 of 160 carry a UEI that IS in
  v6 — they are the same registrations under a different name string, and
  recovering them would have created up to 158 duplicate enterprises. Recorded
  as observed name variants instead.
* **`relationship` is emitted as the literal `unspecified`, never blank.** v6
  states no relationship word, so `canon_rel` classes these
  `unspecified`/`affiliation`. A BLANK is coerced by
  `stage_build`'s `x.get("relationship") or "subsidiary"` and publishes as
  `relation_class = ownership`; it did, on 3,189 rows, until invariant **W3**
  caught it.

* **An APPLIED CORRECTION outranks the file.** The owner's v6 predates
  finding **FA-01** and re-asserted `BRISTOL BAY AREA HEALTH CORPORATION`
  under Bristol Bay Native Corporation, a link Cedar withdrew on 2026-08-26
  and marked tier X. `1133` now reads `cedar_correction_register.csv` (254
  applied pairs) and refuses any edge that re-imports one. Invariant **W7**.
  **An old file is a time machine**: any pass importing a dataset built before
  a correction will re-assert what the correction withdrew, and it arrives
  looking like coverage.

**Consequence.** NEST 1,610 → **4,798 enterprises** (3,189 carrying
`source_id = OWNERV6`), 3,190 ids minted, 472 owner hubs, relations
3,789 → 7,559. `1072 verify` PASS on all 8 invariants; `1102` (the enricher)
must run LAST after any rebuild.
<!-- END ADR-034-OWNER-V6-BUILDER-INPUT -->

<!-- BEGIN ADR-035-PUBLICATION-RULES-ONE-MODULE -->

## ADR-035 — the publication rules are ONE importable module, and text-scraping a rule out of another script is banned

**Decided 2026-09-02** by workstream `CONSOLIDATE-PUBLICATION-RULES` (number
1138 claimed and released), `code/cedar_publication.py`.

**Context.** Owner, 2026-09-02: *"if we can consolidate files to process stuff
to make it easier, fact check — this should be a well oiled machine, not
running in circles over and over again."*

Four scripts write customer-facing extracts — `760_collection_descriptors.py`,
`770_sample_extracts.py`, `1135_full_dataset_review_bundle.py`,
`1137_customer_dataset_combine.py` — and they agreed about the publication
rules by **reading each other's source code with regular expressions**. Five
such scrapers were live:

| # | scraper | reads | out of |
|---|---|---|---|
| 1 | `770._760_product_id_map()` | `PRODUCT_ID` | 760 |
| 2 | `760._flagship_map()` | `FLAGSHIP`, `SPINE` | 770 |
| 3 | `1135._from_770()` | `NEVER`, `GATES` | 770 |
| 4 | `1137._from()` | `NEVER`, `GATES`, `FLAGSHIP`; `COLLECTIONS` | 770; 500 |
| 5 | the product repo's `scripts/import_cedar_manifest.py::_flagship_map()` | `FLAGSHIP` | 770 |

Two of those were already broken and neither was noticed by anything:

* **Scraper 4 failed OPEN.** Its regex could not match the annotated binding
  `COLLECTIONS: list[dict] = [`, so `shelves()` returned `{}`, every collection
  failed the shelf test, and `1137` printed **"0 customer shelves" and exited
  0**. A confident report of nothing.
* **Scraper 1 was never called.** `770` defined `_760_product_id_map()` with
  the comment *"so drift is a hard failure rather than two files quietly
  disagreeing"*, and no call site existed anywhere in the tree. A gate that is
  defined and not invoked is not a gate.

And `DROP_COLS` and `YEAR_COLS` were plain duplicated literals in **1135 and
1137**, with no scraper and no comparison at all — two hand-maintained copies
of a licensing rule, which is worse than the scraping because at least the
scraping was trying.

**THE STATED JUSTIFICATION WAS FALSE, AND IT IS MEASURED.** Every one of the
five scrapers carries some version of *"a module whose name begins with a digit
is not importable, and 770 does file work at import time."* **Both halves are
wrong.** The `import` STATEMENT cannot name a digit-leading module;
`importlib.util.spec_from_file_location` imports it without complaint. And
importing `770_sample_extracts.py` takes **0.04 s** and reads no table — every
file read is inside `main()`, behind `if __name__ == "__main__"`. The scraping
was never necessary.

**Decision.** `code/cedar_publication.py` — an importable name, alongside the
existing `cedar_pipeline.py` / `cedar_extent_competed.py` precedents — is the
single copy of `NEVER`, `GATES`, `FLAGSHIP`, `SPINE_TABLES`, `PRODUCT_ID`,
`DROP_COLS`, `YEAR_COLS`, the shelf sets and `row_ok()`. 760, 770, 1135 and
1137 IMPORT it. All five in-tree scrapers are gone.

**A regex over source text fails OPEN; an import fails CLOSED.** That
difference is the whole argument, and it is why the fix is not "a better
regex."

**`SPINE` had to be renamed, and the gate found it.** 770 used the bare name
`SPINE` for a *set of table names*; 1135 and 1137 both use `SPINE` for the
`data/spine` *directory* `Path`. Three files, one name, two unrelated types,
kept apart only by the fact that none imported another. The shared constant is
`SPINE_TABLES`; 770 imports it `as SPINE` so its local usage is unchanged. The
divergence gate caught this on its first run — nothing else ever could have.

**760's spine scrape was a live hazard, not just clutter.** It ended
`if j >= 0 else set()`, so the day 770 stopped carrying a `SPINE = {` literal
it would have returned an EMPTY set, silently, and every spine-resident
flagship would have been reported as an unclaimed table. That day was
2026-09-02.

**THE ONE COPY THAT REMAINS, AND WHY.** Consumer 5 lives in the PRODUCT repo on
branch `claude/real-collections-manifest`. That branch and `master` are
disjoint trees in one repository and never merge, so a change here cannot reach
it; it does `text.find("FLAGSHIP = {")` against `770_sample_extracts.py` and
`raise SystemExit` when the dict is absent. Deleting 770's literal would break
a live consumer. So `770` keeps a `FLAGSHIP = {...}` literal that is
**generated, not maintained**: `py -3 code/cedar_publication.py sync` writes
it between markers, 770 `assert`s it equals the module at import, and `verify`
fails if it drifts. Two copies, one derived, with a runtime assert and a gate.

**The gate.** `py -3 code/cedar_publication.py verify`, wired into
`846_session_audit.py` as claim 30. Seven checks: every consumer resolves the
shared names to the module's values; no scraper has been reintroduced; the
generated compat literal parses to the same dict under **both** external
scrapers' exact expressions; the storefront and build sets are 12 and 13; every
built collection names a flagship; `DROP_COLS` is all lower case (every
consumer compares `col.lower() in DROP_COLS`, so an upper-case entry could
never match and would silently ship).

**Behaviour is preserved and it was measured, not asserted.** Old and new code
were run against the same live tables in two shadow trees (`code/` copied,
`data/` `docs/` `review/` junctioned, `dist/` separate). `770` and `760`
produce **byte-identical** stdout and outputs. `1135 samples` likewise. `1137`
was run in `plan` only — a concurrent workstream owns its build — and its
constants and gate function were proved equal instead.

**One behaviour DID change, deliberately: `1137 plan` no longer writes
`MANIFEST.csv`.** It printed "nothing written" and then overwrote the manifest
anyway, with dry-run values — no `files`, no `largest_mb`, no codebook, no join
columns, because none of that work runs under `dry`. The manifest is the only
record of what was DELIVERED, and `verify` reads it to decide whether a
spreadsheet on disk is an orphan, so a `plan` turned thirteen delivered
datasets into thirteen apparent orphans while reporting that it wrote nothing.
Found by doing it.

**Consequence.** 5 in-tree scrapers → 0. `NEVER`/`GATES`/`FLAGSHIP` 3 copies →
1. `DROP_COLS`/`YEAR_COLS` 2 copies → 1. `row_ok()` 3 bodies → 1.
`846_session_audit` 29 claims → 30.
<!-- END ADR-035-PUBLICATION-RULES-ONE-MODULE -->

<!-- BEGIN ADR-036-BUILD-VS-STOREFRONT -->
## ADR-036 — the BUILD set and the STOREFRONT set are different sets, and gaming is the thirteenth built dataset

**Decided 2026-09-02** by workstream `GAMING-THIRTEENTH-1141`,
`code/cedar_publication.py`, `code/1137_customer_dataset_combine.py`,
`code/1141_gaming_quality_pass.py`.

**Context.** Owner, 2026-09-02: *"you're always working on thirteen datasets,
the twelve in Cedar Press, and then the gaming dataset. Those are the ones that
you're always prioritizing."*

`1137` decided membership with one tuple, `CUSTOMER_SHELVES = ("standard",
"pro")`, and that tuple was answering two different questions at once: **where
is this sold** and **is this delivered**. `gaming` is `shelf: grove` — it goes
out through Cedar Grove and appears on no Cedar Press shelf — so the single
test excluded it from the combined-product build as well. It is the **largest
maintained collection in the project**: 65 tables, 56 of them shippable. It had
no combined spreadsheet, no `gaming__CODEBOOK.md`, and no notes, and
`846_session_audit`'s CRITICAL claim was green the whole time, because that
claim also counted the storefront.

**Decision.** Three named sets in `cedar_publication`, and every consumer says
which it means:

```
STOREFRONT_SHELVES  = ("standard", "pro")           12   sold on Cedar Press
GROVE_SHELVES       = ("grove",)                     1   sold through Grove
BUILD_SHELVES       = STOREFRONT + GROVE            13   delivered
```

`CUSTOMER_SHELVES` survives as an alias for the storefront, because that is
what it always meant. `MANIFEST.csv` gains `storefront` (Y/N) and
`sold_through`, so a reader of the OUTPUT cannot re-conflate them either.

**The property that could not be lost.** The count was hard-coded because **a
silent extra dataset is a defect** — `newsletters` shipped as an unwanted
thirteenth storefront slot before the owner withdrew it and nothing failed. It
now holds three ways, all in `1137 verify`: a thirteenth STOREFRONT slot fails
the storefront count; a fourteenth BUILT dataset fails the build count; and a
spreadsheet on disk that no manifest line claims fails outright. The third is
new and is the one the old check could not see. Proved by fixture: dropping
`newsletters.csv` into `dist/customer/` turns `verify` red and names it.

**Two defects the gaming build exposed in `1137` itself, both fixed generically
for all thirteen.**

1. **The shared join key was the first one DECLARED, not the finest one both
   tables carry.** `gaming_facilities` declares `[tribe_id, cedar_uid,
   entity_id, facility_id]` and its grain is the PROPERTY. Every one-to-many
   count column therefore counted the property's whole NATION — Cherokee
   Nation's ten casinos each reporting the tribe's total under a column named
   for the property. Keys are now ranked by how finely they cut the flagship.
   Effect on gaming: four more tables meet the one-to-one test at facility
   grain and fold in properly, and every count means what its row means.
2. **A `plan` run overwrote `MANIFEST.csv` while printing "nothing written".**
   Fixed the same hour (independently, by the owner) — recorded here because
   the manifest is what `verify` reads to decide whether a spreadsheet is an
   orphan, so a dry run could turn twelve delivered datasets into twelve
   apparent orphans.

**Column ORDER, not column deletion.** `gaming` lands at 311 columns where the
other twelve are 29–91. Most of that width is Cedar's provenance quartet per
measured fact (`gaming_machines` · `_value_basis` · `_observation_status` ·
`_observed_date`), which is the product's differentiator, and `770` rule 6
already forbids dropping columns because it makes the schema depend on which
rows shipped. So `order_columns()` bands every dataset's header — identity,
substantive, provenance, then joined grouped by source table — as a **stable
permutation that raises rather than lose or duplicate a column**. Nothing is
removed and the first screen is readable.

**Consequence.** 13 spreadsheets, 13 codebooks, 13 notes pairs. `846`'s
CRITICAL claim now asserts 13 built / 12 storefront / 1 Grove.
<!-- END ADR-036-BUILD-VS-STOREFRONT -->

<!-- BEGIN GAMING-DENOMINATOR-717-CORRECTION -->

## CORRECTION 2026-09-02 — the gaming property denominator is 717, not 714

Appended by `code/1142_gaming_denominator_doc_sweep.py`. **No prose above this
line was edited**, per the rule the `GAMING-DENOMINATOR-2026-09-02` banner set
for itself.

Any figure in this document that uses **714** as the count of distinct gaming
properties is superseded. The settled figure is **717**:

```
787   rows in gaming_facilities.csv
-16   carrying cedar_place_id_absent_reason = NOT_A_PLACE
=771   rows that are a place
-54   extras collapsed by the 53 ADJUDICATED merge groups
=717   distinct properties        <- COUNT(DISTINCT cedar_place_id)
```

**Why the old ladder gave 714.** It subtracted **57** duplicate extras found by
name normalisation. The adjudication found **54**. The three-property
difference is three groups a mechanical duplicate test called the same property
and a human verdict did not:

| group | why it is two properties |
|---|---|
| `THREE RIVERS` (OR) | Coos Bay 97420 and Florence 97439 — **67 km apart**, two casinos |
| `GLACIER PEAKS` (MT) | a casino and its hotel |
| `CITIES OF GOLD` (NM) | a casino and its hotel |

A duplicate count is an upper bound on merges; an adjudication is the answer.

**Two groups remain genuinely open** and either ruling moves 717: `THE STABLES`
(a real Miami/Modoc joint operation — one property, two sovereigns) and
`7 CLANS FIRST COUNCIL` (OK). Both are in
`review/OWNER_DECISION_QUEUE.md` as GP-1 and GP-2.

**Do not re-derive this number.** Seven values circulated for it — 787, 780,
734, 727, 725, 717, 714 — each from a correct-looking rule applied to an
undefined question. `gaming_facilities.csv` now answers it itself: the 16
non-places carry a reason column, and the merged properties share a
`cedar_place_id`. Read `COUNT(DISTINCT cedar_place_id)`.

<!-- END GAMING-DENOMINATOR-717-CORRECTION -->

<!-- BEGIN ADR-037-LINKAGE-COVERAGE -->
## ADR-037 - linkage coverage is a RATCHETED product metric, and a low figure is not automatically a defect

*Decided 2026-09-02 by workstream LINKAGE. `code/1139_linkage_coverage.py`
(measure, gate) and `code/1140_linkage_close.py` (close the gap). Fifteen
minutes of reading `docs/LINKAGE_COVERAGE.md` replaces this section; what is
here is the four decisions and why the obvious alternative to each is worse.*

### 1. LINKED is the CONJUNCTION, never the key column alone

Every flagship in this product has more than one column that looks like the
answer, and on three of them the columns disagree by a named population:

| table | key column says | gate column says | apart |
|---|---:|---:|---:|
| `prime_contracts` | `tribe_id` 791,490 | `attributed_flag` 791,394 | **96** |
| `federal_funding_transactions` (before this pass) | `tribe_id_neid` 552,602 | `attribution_status` 553,106 | **504** |

The 96 are `Nakupuna Solutions, Llc` at `RULED_TIER_C_NOT_ATTRIBUTED` -
$269,771,379 of NEGATIVE ruling that the key column counts as coverage. The
504 were `Bristol Bay Native Corporation`, keys cleared by the FA-01 unlink
and status columns left claiming an attribution - $494,305,407.20. **A
numerator that reads only the key column sells both.** So LINKED is the
conjunction of every column a consumer branches on, which is always the
smallest available reading, and each sibling column is published beside it
with the disagreement stated in rows.

**Rejected: pick the "right" column per table.** There is no right column
while two of them disagree; there is a defect, and the disagreement is the
thing worth publishing.

### 2. A dataset declares WHICH ENTITY the link names

`native_owned_businesses.business_entity_id` is populated on 4 of 2,916 rows.
Read as the numerator that is 0.14% and it is a true statement about the
wrong column: `identity_scope` says these firms are owned by PEOPLE
(`any_native` 1,567, `citizen` 385, `shareholder_descendant_or_spouse` 98),
280 rows' names ARE natural persons, and `resolution_method` shows the
resolver already REFUSING loose-token matches on `Cherokee Nation`, `Navajo`
and `Eagle`. A sole proprietor is not a spine entity and minting one would be
fabrication. The Native entity the row is ABOUT is the certifying nation, at
2,767 of 2,916 (94.87%).

So every dataset carries a `role` sentence naming which entity the link
identifies, and the numerator reads the column for that role.

### 3. A LIST-VALUED key is declared, not inferred

`nagpra_notices` has no `cedar_uid`, `tribe_id` or `entity_id`. It carries six
pipe-delimited role columns, because one notice names many parties in many
roles. **A scan looking for the three usual id names reports 0% on a dataset
that is 90.83% linked**, and that scan was run on this product before it was
caught. `list_keys` declares them and LINKED is their union. Verified against
the table's own `has_resolved_entity`: 6,169 both ways, **0 rows disagreeing
in either direction**. The structural predicate is used rather than the flag
because it survives the flag being dropped.

### 4. THREE denominators, all correct, and the ratchet runs on the rawest

- **rows in `data/clean`** - the whole table.
- **rows that are `publishable = Y`** - what the customer file holds.
  `native_owned_businesses` is 2,916 and 2,044. Neither is wrong; a figure
  quoted without saying which one is.
- **rows that CAN name an individual entity.** `natural-resources` reads
  **6.24%**, and 9,791 of its 10,600 unlinked rows are
  `aggregate_suppressed_by_publisher` - ONRR and the state publishers report
  Indian Country revenue in AGGREGATE and never name a recipient. That is
  `SOURCE_DOES_NOT_PUBLISH`: a fact about the world, never a Cedar
  deficiency, and keying those rows would be fabrication. Against the 957
  rows a recipient CAN be named on, the same table is **73.67%**. Same shape
  in `nonprofits` (11.15% raw, **18.23%** of 7,804 once the 4,960 EXCLUDED_*
  rulings are removed) and in `contractors` (64.99% raw, **68.50%** of
  1,153,140 once `RULED_NOT_NATIVE` and `RULED_CLASS_ONLY` are removed).

**The exclusion must be a DECLARED, PER-ROW, source-side or ruled fact,
never a judgement made by the measuring script**, and `RULED_OWNER_NOT_IN_
SPINE` is deliberately NOT in any of these sets, because that one IS a Cedar
gap. **And the ratchet runs on the RAW figure**, so the third denominator can
never be used to make a real fall look like a change of definition.

### 5. The ratchet lives with the measurement, not in `62`'s baseline

`62_no_regression_check.py` carries ONE new MUST_BE_ZERO counter,
`linkage_metrics_below_floor`, answered from `1139`'s OWN baseline - the same
arrangement as `293` and `845`. Seeding twenty-eight new metrics into `62`'s
baseline would have required re-recording it, which bakes in whatever else is
red that day; standing rule 15 forbids it. This way the gate is live the
moment it lands.

Two counters per dataset. `linkage_<d>_bp` is the ratio, with a **25 basis
point** tolerance, because several flagships are rebuilt by other workstreams
and a rebuild that adds honest unlinked rows lowers a ratio without losing a
link. `linkage_<d>_rows` is the absolute count of linked rows and has **no
tolerance at all**, so links being lost while the ratio holds still fails.
`1139 selftest` proves both fire.
<!-- END ADR-037-LINKAGE-COVERAGE -->

<!-- BEGIN ADR-038-PRIME-SUB-NEVER-COMBINED -->

## ADR-038 — prime and sub are two numbers with two labels, never one

**Status:** accepted, 2026-09-02, workstream MONEY-RECON-1144
(`code/1144_money_reconciliation_prime_sub.py`).
**Supersedes nothing. Settles a question that had been asserted and never
measured.**

### Context

`docs/MONEY_TOTALLING_RULES.md` has said since 2026-09-01 that *"a subaward is
a slice of a prime award Cedar already publishes… never add the two."* That was
a correct instinct with no number behind it. A past article reported a combined
prime+sub total while its chart showed primes only, and nobody could say by how
much the article was wrong.

### The measurement

Of $34,906,694,737.65 in countable subaward dollars (69,921 filings), joined on
`prime_award_unique_key` → `prime_contracts.contract_award_unique_key`:

- **$13,612,271,637.21 (39.0%, 27,319 filings) sits on a prime award Cedar
  already publishes**, and **$13,500,614,272.77 of that (99.2%) is on a prime
  row that is itself `attributed_flag = 1`** — inside the published
  $230,259,821,658.99 attributed prime total.
- $21,294,423,100.44 does not, and it is **not one thing**:
  $19,317,140,197.29 is `b_native_as_subawardee` (a non-Native prime paying a
  Native sub), $1,439,559,118.53 is `a_native_as_prime` on awards missing from
  the prime table, $499,305,405.62 is `both_sides_native`, $38,418,379.00 is
  `unknown`.

### Decision

**Cedar publishes no combined prime+sub figure.** A naive sum fails three ways
at once and only the first is a double-count:

1. it re-counts $13.61B of federal dollars obligated once;
2. it merges FPDS (**government-recorded**) with FSRS (**vendor self-reported
   by the prime, unvalidated**) into one number a reader cannot discount;
3. it launders a coverage gap into growth — the $1.44B of `a_native_as_prime`
   on awards absent from `prime_contracts.csv` patches the prime table from the
   sub table on 3,944 awards and nowhere else.

**The permitted presentation is two labelled figures.** The only slice of the
subaward file that is neither a re-slice of a published prime nor a patch over
a prime-table gap is **`b_native_as_subawardee` on primes Cedar does not carry:
$19,317,140,197.29 over 37,850 countable filings**. It may sit *beside* the
prime total, never inside it, and its sentence must say "self-reported by the
prime."

### Consequences

- Any product surface offering "total federal dollars" must pick FPDS or FSRS
  and say which. A toggle is acceptable; an addition is not.
- The reconciliation is a **ceiling, not an identity**: on the 7,305 awards
  where both sides are present, subs total $13.61B inside $41.12B of prime
  obligations, and **444 awards have subs exceeding their prime by
  $1,737,942,789.89** — they pass `subaward_exceeds_prime_flag` because that
  flag is per FILING against the source's `prime_award_amount`, not per AWARD
  against Cedar's summed obligations. No product may claim the two tables
  reconcile more tightly than that.
- Re-derive, do not quote: `py -3 code/1144_money_reconciliation_prime_sub.py
  measure`. `verify` exits 1 when any of ten recorded numbers stops
  reproducing and `selftest` proves all ten fire on a perturbed value, so a
  PASS is evidence the measurement ran rather than evidence nothing broke.

<!-- END ADR-038-PRIME-SUB-NEVER-COMBINED -->
