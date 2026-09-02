# Cedar Press — external design review, ROUND 2

*Paste this whole document into ChatGPT (or another model) and ask it to find
flaws. Self-contained; no repository access needed. Every number is measured,
not remembered. Generated 2026-08-30.*

---

## Read this first

You (or a model like you) reviewed this system once already. **That review was
correct on every falsifiable claim**, including one exact piece of mathematics.
It has since been implemented, not just acknowledged: five parallel workstreams,
~24 commits, every claim re-executed and verified by a session that did not make
it.

**So do not re-litigate round 1.** Round-1 findings and their disposition are
summarized below only as context. Your job is to attack **the new architecture**
— the source-record layer, the temporal/observation model, the release manifest,
the per-predicate policies, and the process machinery — plus anything in the
honest-weaknesses section.

**Be adversarial and concrete.** For each numbered question, try to construct a
specific failure: an input, an ordering of events, an edge case where the
mechanism gives a wrong answer, silently loses data, or lets two agents disagree
undetected. Rank findings by severity. Where a mechanism is sound, one line and
move on. **Say explicitly which findings you constructed a failing case for
versus merely suspect** — round 1's most valuable output was the half you could
demonstrate.

Cedar Press is a commercial dataset about Native American / Alaska Native /
Native Hawaiian entities — tribal governments, ANCSA corporations, tribal
enterprises, Native nonprofits — and their federal funding, contracting, gaming,
lobbying and ownership. Buyers join on our entity IDs, so our identity errors
become theirs.

---

## Round 1 disposition (context only — do not re-review)

| finding | outcome |
|---|---|
| Check code has minimum symbol distance 2, null vectors at payload pairs (1,3)(1,5)(2,4)(3,5) | **Verified exactly by exhaustive search.** Documented as a precise V1 guarantee; NOT re-minted (1,536 uids stamped across 125 tables; a registry-existence check already rejects unknown uids). RS[7,5,3] over GF(32) is the accepted V2 if uids ever become hand-keyed. |
| One identifier could bind to two entities with no conflict row | **Was true by discipline, not construction** (measured 0 violations across 4,069 UEIs). Now invariant **I10**, fixture-proven. |
| `entity.registration_state` at the wrong grain | **Verified**: 113 entities carried multiple values, one with 35, none pointing at its registration. Facts now have subject **(entity, qualifier)**. This exposed a second error of ours: "corroborated" fell 38 → 2, because 36 were different registrations' names collapsed onto one entity. |
| `resolved` ≠ supported; R07 manufactures certainty | `support_status` added orthogonal to `resolution_status`; R07 **barred** from deciding identity-critical predicates (ties → `UNRESOLVED_TIE`, candidates preserved). |
| Metric contradiction (0 two-source vs 38 families) | **Our reporting error.** Both true at different scopes. Also accepted: "0 disagreements" is *undefined*, not zero, when nothing overlaps. |
| F1 — source→UID link not separately modeled | **Implemented** (see §1). And found LIVE: three ANCSA *corporations* were carrying "federally recognized" at tier A with `support_status = authoritative`. |
| F5/F11 temporal + observation | **Implemented** (see §2). |
| F13 replay | **Partially closed** (see §3). |
| F10 global precedence, F9 grain, F6 handles | **Implemented** (see §4). |
| F8 registration vs legal entity | **Analysis + proposal only**, deliberately not built (see weaknesses). |

---

## 1. The source-record layer (new)

The old defect: assertions began *after* a source row was resolved to a
`cedar_uid`, fusing "what the source says" with "who we think it means", so an
authoritative source could launder a bad match into an authoritative fact.

Now three claims are separately representable and separately refutable:

```
source record R asserts   official_name = N     <- authority applies HERE
source record R asserts   recognition   = yes   <- authority applies HERE
source record R refers_to candidate uid G       <- authority NEVER applies here
```

- `cedar_source_records.csv` — **575 nodes**, and **no `cedar_uid` column at
  all, by construction**: a source record cannot mention a Cedar entity, so a
  match cannot hide inside a statement of fact.
- `cedar_source_record_links.csv` — **585 links**, each with its own route,
  evidence, candidate set, and status: `proposed` 570, `contested` 7,
  `denied` 5, `unresolved` 2, `verified` 1.
- A dataset declares `eligible_entity_classes`. The Federal Register roster of
  *recognized tribal entities* enumerates governments, so it **cannot** name an
  ANCSA corporation. Invariant **SR7** makes the F1 rule mechanical: a link may
  never cite its source's authority as its own basis.
- The harvester no longer resolves anything itself — it emits only from links
  with status `verified`/`proposed`, and every assertion carries its `link_id`,
  `link_status` and `match_route`.

**Effect measured:** +3 records gained (three Alaska villages now land on the
village *governments* rather than being refused because the only offer was a
corporation), 0 lost, 0 repointed; the 9 wrong authority-bearing facts are gone
and verified gone.

**Questions**
1. `refers_to` has a status but the *fact* assertions from that record are
   emitted for both `verified` and `proposed`. Construct a case where treating
   `proposed` as good enough to emit is wrong — and say what the alternative
   costs (570 of 571 accepted links are `proposed`; only 1 is `verified`,
   because no genuinely independent second matching route exists for this
   source).
2. `eligible_entity_classes` is a **human judgement written in code** with its
   reasoning recorded, not derived from anything. Where does that fail?
3. One dataset is migrated; every other harvester still fuses the two claims.
   What is the risk profile of a *partial* migration specifically — is a
   half-migrated system worse in any way than the uniform old one?
4. A "class-eligible unique match" is now the accepted route. What kinds of
   wrong match survive a class filter?

## 2. Temporal facts + observations (new)

Three clocks are now separate: **validity** (`valid_from`/`valid_to` — true of
the world), **source effective date** (what the source says, if stated), and
**observation** (when we looked).

- `cedar_temporal_facts.csv` — **2,867 claims**. `valid_from` **KNOWN on 85,
  UNKNOWN on 2,782**, and audited: **zero rows flagged unknown carry a date
  anyway.** No interval was made tidy by inventing a boundary.
- `cedar_observations.csv` — **35,741 events** `(claim_id, retrieved_at,
  snapshot, verifier, result)`. Re-observing a claim leaves the claim table
  **byte-identical** (md5-verified) and appends an event; a duplicate call is
  refused. That is the F11 fix.
- Observations are split **derived** (rebuilt each run, every dropped row
  counted *and named*) vs **event** (never rebuilt, never dropped), so a
  concurrent rebuild elsewhere cannot hold the gate permanently red.

**What it priced.** One streaming pass over 1,217,768 transactions, resolving
ownership *as of the transaction date*:

```
RESOLVED                  498,410 tx   $141.0B
UNKNOWN_OUTSIDE_EVIDENCE   72,369 tx    $22.9B
AMBIGUOUS_OVERLAP          41,991 tx    $10.5B
NO_FACT_ON_SUBJECT          9,501 tx     $2.9B
NO_COVERING_FACT              608 tx     $0.3B
AMBIGUOUS_GRANULARITY          75 tx     $0.07B

of which: 110,705 tx ($32.1B) ship an owner we cannot CONFIRM at that date
            9,402 tx  ($2.1B) ship an owner the temporal layer CONTRADICTS
```

**What the data turned out to lack** (measured, not assumed): there is **no
join** between our 189 dated ownership deals and our 2,684 ownership edges. A
strict automated bridge produced 480 candidates that matched the **acquirer's**
tribal name rather than the acquired firm — rejected on measurement, replaced
by one curated cited row. Only 84 of 189 deals state a real effective date; 37
carry a full `YYYY-MM-DD` while saying "month-level only"; **5 explicitly
disclaim their own closing date in prose**, so a keyword match on "closing"
reads all 5 backwards.

**Questions**
5. Ownership intervals are mostly **observation-bounded**, not
   statement-bounded (85 of 2,867 have a known `valid_from`). What breaks when
   an interval's edges are "when we happened to look"? Is
   `UNKNOWN_OUTSIDE_EVIDENCE` an honest answer or a hidden default?
6. `AMBIGUOUS_GRANULARITY` arises because contract data carries only fiscal
   year while a sale has a day. What is the correct semantics for a fact whose
   validity boundary is finer than the grain of the data it must key?
7. Attack the derived/event observation split — can a "derived" projection
   silently disagree with the events it was derived from?
8. Is *re-observation without change* the same evidence event as *first
   observation*? Should recency rank them equally?

## 3. Release replay (new)

- Manifest per collection: commit **plus per-script `matches_commit`**; every
  transitive input; sha256 per file and a merkle hash per directory; a
  **retained content-addressed immutable copy** (read back and re-hashed before
  it is called retained, then set read-only); provenance with a named retrieval
  procedure; environment lock; frozen config; ordered commands; manual-decision
  inputs; output schema, primary key, hashes, row counts, conservation checks.
  The verdict is **computed and tiered**, never asserted.
- **4 collections replayed** in clean rooms built from the blob store with
  nothing read from the live tree; 76/76 inputs retained (~3.0 GB); 25 tables
  compared; **4 byte-identical**.
- Input discovery uses multiple channels because one is provably insufficient:
  the declared-IO channel **missed the 18.2 MB corpus an entire dataset is
  parsed from**. Undiscovered reads 236 → 203.
- **Determinism fix:** a `fetched_date` column held the wall clock, so a table
  could never be byte-identical. It now derives from the cached artifact's
  mtime, and is empty when unknown rather than falling back to the clock. That
  table now hashes identically across runs.
- **De-hardcoding:** 297 of 298 scripts that hardcoded the absolute project
  root now derive it; 307/307 equivalence proofs *executed* (each derived
  expression evaluated from the file's real location and compared to the
  literal from git). One deliberate exception: the replay tool itself must keep
  recognizing the literal, because it checks out *past* commits that all
  contain it. A lint class guards against any new literal, and carries no
  literal of its own.

**Questions**
9. A retained blob store proves *what the input was* only if it is itself
   durable. What is the failure model of a single-machine content-addressed
   store, and what would you require before calling a release replayable?
10. Deriving `fetched_date` from an artifact's **mtime** made the table
    deterministic — but mtime is not a fetch. Attack that choice.
11. Blocking components are detected *from the live tree before any replay
    runs*. What can only be discovered by actually replaying?
12. **The near-miss worth attacking:** the input-discovery resolver recognized
    project paths **by matching the hardcoded root literal**. Removing the
    literal would have blinded the only channel that sees a critical corpus —
    and `verify` would still have exited 0, because verify only re-hashes blobs
    it was *told about*. It was caught by reading the resolver, not by any
    test. **What other checks in this design can pass while being blind?**

## 4. Resolution policies, grain, handles (new)

- **Six per-predicate policies** replace one global order, each owning its
  rank order plus three deny semantics: a non-authority deny can no longer
  pre-empt authority (an authority *retracting itself* still can); an old
  equal-tier deny can no longer permanently suppress a newer affirmation; stale
  sources no longer out-corroborate one current source. A blocked deny is
  **kept** as a conflict row. Measured effect on live data: **zero facts moved**
  — all 332 denies sit on predicates that declare no authority, so the defect
  was structural and unreached.
- **Grain**: a declaration is grain + primary key + join keys + join
  cardinality, **validated against the file every run**; a contradicted
  declaration is release-blocking. **Unstated-grain shippable tables: 207 → 28.**
  Keys were confirmed on the FULL file (hash-then-literal, so no birthday
  collisions). `join_cardinality = "one"` only where proven, because "one" is a
  promise.
- **Handles**: the bug was worse than the finding — the mint keyed its
  existing-uid lookup on the *handle*, so a reclassification missed and **minted
  a second uid for an entity that already had one**. Now a handle↔uid history
  table retains every binding; an old handle always resolves to the same uid; a
  retired handle pointed at a different entity raises.
- **Semantic diff**: the baseline snapshots content, and the gate reports when
  facts change winner / support / status / entity uid / parent / class **while
  row counts stay identical**. `sem_entities_uid_reassigned` is MUST_BE_ZERO.
- **Row conservation**: every harvested row lands in exactly one **named**
  bucket; `other`/`unknown`/`misc` are refused as reasons. 83,676 read, 0
  unaccounted, 25,434 rejected and all named.

**Questions**
13. Six policies instead of one order: what is the failure mode of
    *policy proliferation*, and how would you detect a predicate governed by
    the wrong policy? (One policy currently governs **0** facts — declared
    ahead of its predicates being harvested, and warned about.)
14. Grain is validated by **uniqueness on the current file**. A key unique
    today may not be unique in principle. What does that miss?
15. Attack semantic diff: what mass change would it *not* see?

## 5. Honest current state (attack these numbers)

```
34,525 assertions   34,185 resolved facts   332 refutations   0 conflicts
```

| support_status | facts |
|---|---:|
| traceable_single_source | 20,358 |
| **legacy_only** (no provenance recorded at all) | **11,649** |
| authoritative | 1,320 |
| unverified_single_source | 832 |
| refuted | 22 |
| **corroborated** (>1 independent evidence family) | **4** |

- **Facts with a second independent source: 13** (all agree; 0 disagree). Up
  from 0. Against a 4,100-row identity-critical unsupported debt, that is a
  demonstration, **not a payment** — and the number is stated that way
  internally too.
- **`identity_facts_legacy_only`: 4,089** — identity-critical facts standing on
  a row with no recorded provenance. Ratcheted; may only fall.
- **28 shippable tables still have unstated grain** (was 207), listed by name.
- **15 tables carry literal duplicate rows** — 80,778 in one contracting table;
  179,259 in another; one ruling ledger is **40% duplicates**. Found by the
  grain probe; routed to pipeline owners; data untouched.
- **`prime_contracts_entity_year`: `(tribe_id, fiscal_year)` collides on 1,751
  of 8,464 rows.** Anyone summing obligations by tribe-year **double-counts
  today**. Open ruling.
- **334 suspect EIN links** surfaced by the first second-source harvest — six
  self-filing entities whose EIN actually files as a *different* organization
  (one Alaska health consortium's EIN files as a language nonprofit in
  Indiana); 328 file from a different state than the entity.
- The IRS "verified strict" file was measured as a **100% echo** of another
  IRS-derived table (1,090/1,090 EINs, 0 differences) and made to emit nothing.
- **Replay:** 4 of 13 collections; 4 of 25 tables byte-identical; remaining
  blockers are stale released outputs, an undeclared enricher writing 96 tables
  it is not planned to write, and 283 run-stamp columns (breakdown produced,
  206 already attributed to script+column).
- **F8 not built**: 3,511 distinct (entity, differing-legal-name) pairs across
  714 entities carrying $173.9B are still modeled as registrations of a parent
  rather than potentially separate legal entities.

**Questions**
16. Given the above, what is the **single most dangerous thing** a buyer could
    do with this data today, and what would you gate to prevent it?
17. `legacy_only` is 34% of all facts. Is capping it at tier C and excluding it
    from corroboration sufficient, or does its sheer volume create a problem
    those two rules do not address?
18. Only **4 facts** are corroborated across 34,185. At what point does an
    "arbitration layer" with almost nothing to arbitrate become
    self-deception rather than infrastructure?

## 6. Process machinery (attack this too — it decides everything above)

- **Handoffs**: a claim of completed work is a row born UNVERIFIED, carrying
  the commit hash and `verify_commands` whose exit 0 constitutes proof.
  Verification **re-executes** them. **Self-verification is refused.** Current
  board: **9 handoffs, 0 unverified, 0 failed.**
- **Fixture standard**: a check does not count until a fixture proves it
  *fires* — inject the violation, exit 1, restore, exit 0. Every invariant
  above was landed this way.
- **Parallel agents**: file ownership declared before editing; no agent
  commits; an integrator verifies claims against live data and commits.
- **Three self-inflicted defects found by this machinery, all reported not
  buried**: (a) a ratchet installed **backwards**, so the gate failed the first
  time the metric improved — found independently by two agents who each proved
  it was not their work; (b) a clean-room replay whose un-rewritten scripts
  wrote into the **live tree** — caught, restored byte-exact, cause fixed;
  (c) a handoff **deadlock** where a handoff's checks included the gate that
  counts failed handoffs, so it could never clear — fixed twice, at two levels.

**Questions**
19. "Verifier must be a different session" — round 1 already noted this is
    administrative, not epistemic, separation. Now that it has run 9 times,
    what would you change to make it real, given that the verifier re-executes
    *the claimant's own* declared commands?
20. What class of defect does the fixture standard systematically **miss**?
21. Three self-inflicted defects in one pass — is that evidence the machinery
    works, or evidence the change rate is too high for it? What would you
    measure to tell those apart?

---

## Constraints (respect these in your answers)

- Proprietary third-party IDs may be held internally but **never shipped**.
- **No authoritative federal roster of Native Hawaiian Organizations exists** —
  that universe is genuinely open; designs must tolerate it.
- Village **government** vs village **corporation** confusion is the single most
  dangerous error class in this domain. Two entities can share a name and be
  different sovereigns (and a tribe's business arm is not the tribe).
- The methodology must remain replicable by a human without AI tooling —
  manual verification steps are a feature, not debt.
- Data is ~46 GB, single workstation, Windows, no cloud budget assumed.

## Deliver

1. Ranked findings, each with a concrete failure scenario, and **explicitly
   marked** as *demonstrated* or *suspected*.
2. One-line acknowledgments where a mechanism is sound.
3. Answers to the 21 numbered questions.
4. **What you would attack next if you had one more round** — and what you'd
   need from us to do it.
