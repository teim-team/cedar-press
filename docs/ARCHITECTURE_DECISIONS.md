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

**Markdown, finished.** 21 (upper bound) → **4**. Eight docs settled by actually
regenerating and diffing, recorded in `MD_PROVEN_SAFE` with their evidence.
`docs/LOBBYING_BUILD_LOG_2026-08-05.md` — the one genuine candidate — is
**"the generator is right and the prose is stale"**: 35 removed lines, 30 of
them unpaired, and **every single one carries a number** with a numeric
counterpart on the added side (39,448 → 40,968 raw filings; the ambiguous
queue 361 → 5 because the rulings were applied). `regen` now counts removed
lines containing no digit at all, which is the shape of a sentence somebody
wrote, and reports zero here.

**The four left are not mine to settle.** `DATASET_READINESS.md` (518),
`GRAIN_AUDIT.md` and `DATASET_CONTRACTS.md` (512) are written by
integrator-owned generators and were not run. `INVENTORY.md` (521) is slow
rather than owned.

**Baseline** re-recorded after the fixes: **0 CSV, 0 class 3, 4 markdown.**
<!-- END ADR-017 -->
