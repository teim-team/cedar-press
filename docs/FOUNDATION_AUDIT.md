# Foundation audit — Phase 0

*Started 2026-08-29 against the mission spec. **No code was refactored in this
phase.** Every claim below is marked as an OBSERVED FACT (a command was run and
its output inspected), an INFERENCE, or an OPEN QUESTION. Behaviour that exists
in code but was not executed is labelled UNVERIFIED.*

---

## F-0. TWO BLOCKING STRUCTURAL FINDINGS, BEFORE ANY OTHER WORK

### F-0.1 There is no single repository root. The spec assumes one.

**OBSERVED.** The mission says *"You are working in the Cedar Press repository"*
and lists `cedar_source_registry/*` among the authoritative materials. Those
materials are not in the same place as the datasets they govern:

| material | `Desktop/Cedar Press` | `Desktop/cedar-press-repo` |
|---|---|---|
| root `CLAUDE.md` | absent | absent |
| `cedar_source_registry/CLAUDE.md` | absent | **present** |
| `cedar_source_registry/HARMONIZED_SCHEMA.md` | absent | **present** |
| `cedar_source_registry/sources.jsonl` | absent | **present** |
| `cedar_source_registry/verification_log.jsonl` | absent | **present** |
| `cedar_source_registry/schema/*.json` | absent | **present** (2 files) |
| the 12 datasets, `code/`, `data/clean/` | **present** | absent |

**Consequence for the spec's hardest requirement.** *"No dataset can reference
an unregistered Cedar source ID without validation failing"* cannot be enforced
today: the validator would live in `Cedar Press` and the registry it must check
lives in a different tree, on a different branch, with no import path between
them. This is the single highest-leverage fix in the mission and it is
**architectural, not cosmetic**.

**OPEN QUESTION for the owner.** Three options, and this is a product decision:
(a) vendor a read-only snapshot of `sources.jsonl` + `schema/` into Cedar Press
with a checksum and a staleness gate; (b) make Cedar Press a sibling package the
repo imports; (c) move the registry into Cedar Press and publish it outward.
**(a) is the smallest change that makes the gate real** and is reversible.

### F-0.2 Per-phase commits are impossible in the tree that holds the datasets. — **RESOLVED 2026-08-29**

**OBSERVED.** `git rev-parse --is-inside-work-tree` in `Desktop/Cedar Press`
returns *"fatal: not a git repository."* `cedar-press-repo` is a git repo, but
the owner's standing instruction (2026-08-28) is that it is the **north star /
showcase**, and datasets go in only when finished.

**Consequence.** The spec's *"Every phase must end in ... its own commit"*, its
release-gate requirement to fail on *"dirty or uncommitted production code"*,
and the handoff schema's `commit hash` field have **no substrate** in the
dataset tree. Every retirement in this project is therefore done by MOVE to
`graveyard/<date>_<reason>/` with an evidence index — that convention is the de
facto version control and it is why nothing here is ever deleted.

**RESOLVED — `git init` in `Desktop/Cedar Press`, commit `2036e46`.** The owner's
ruling settled it: *"ultimately, this work is gonna eventually live in a single
repo. So you can build whatever. And we have a folder called Cedar Press. It
doesn't matter, that folder is the repo."* The audit had treated the north-star
instruction as a prohibition on committing anywhere; it was a rule about what
gets *showcased*, not about what gets *versioned*. Recording that so the same
wrong inference is not made again.

The tree tracks **990 files, 38.8 MB** — source only. Content is excluded by
extension at any depth, which matters because data here does not live in
`data/`: 2.5 GB sat in `Federal Spending/`, 139 MB in `code/lobbying_pull/`,
21 MB of scraped pages in `code/ancsa_portal/txt/`, and loose `.dta` files at
the repo root. A directory-based rule missed all four. `data/spine/cedar_identity_register.csv`
is the one deliberate exception: every table references it, so a silent edit to
it would otherwise be undetectable.

**The substitute is still wanted, and is now complementary rather than a
replacement.** A commit hash pins the *code*; it says nothing about whether the
38 GB the code read was the same 38 GB. `run_id` + `code_version` + input/output
logical checksums remain the only thing that can attest to the data side, and
the handoff schema should carry **both**. Revert of data stays manual via
`graveyard/` and `.bak_*` — git does not and should not cover it.

---

## F-1. THE LARGEST GAP: THERE IS NO ASSERTION LAYER

**OBSERVED.** Searched `data/clean/` for the spec's core model:

| concept | tables found |
|---|---:|
| `*assertion*` | **0** |
| `*lineage_root*` | **0** |
| `*resolved_view*` | **0** |
| `*crosswalk*` | 3 |

**This is the spec's most important non-obvious requirement and it does not
exist.** Cedar today **overwrites facts**: a build picks a value and the losing
value is gone. There is no `assertion_id / field_name / asserted_value /
source_id / source_snapshot_id / observed_at / valid_from / valid_to /
parser_version / confidence` row anywhere.

**What partially substitutes, and where it stops:**

- `cedar_identifier_ledger_final.csv` is assertion-shaped for **identifiers
  only** — it keeps `confidence_tier`, `attribution_method`, `tier_rationale`,
  `is_authority` per identifier, and preserves tier-X *negative* rulings rather
  than deleting them. That is the right shape, applied to one field family.
- `cedar_identifier_graph_edges.csv` (46,051 edges) carries `edge_tier`,
  `edge_tier_source`, `asserting_source`, and **12,136 `BLOCK` edges** — refusals
  preserved as evidence. Again the right shape, again identifiers only.
- `cross_reference.jsonl` in the registry carries a binding `do_not_infer`.

**INFERENCE (high confidence):** the pattern the spec wants already exists and
is proven in the identifier layer; it has simply never been generalised to
non-identifier fields (name, address, ownership, revenue, status). Phase 3
should **extend the ledger's model**, not invent a new one.

### F-1.1 Self-confirmation is currently possible

**OBSERVED.** No `lineage_root_id` or equivalent exists in any table. **OPEN
QUESTION / UNVERIFIED:** whether any two Cedar datasets currently treat the same
upstream publication as independent corroboration. The registry *does* guard the
adjacent case — `cross_reference.jsonl` rows carry `do_not_infer`, and
CLAUDE.md's evidence hierarchy forbids a Cross-Reference source from originating
an ownership assertion — but that governs **source class**, not **shared
evidence family**. A mirror and its原 publication would both be "Cross-Reference"
and neither rule would fire.

---

## F-2. WHAT THE SPEC ASKS FOR THAT ALREADY EXISTS

**OBSERVED — do not rebuild these.** The spec says to adapt to the repository
rather than impose a disconnected framework; here is what it would be
duplicating.

| spec requirement | existing implementation | state |
|---|---|---|
| dependency cycle detection, pipeline | `cedar_pipeline.KNOWN_ORDERINGS` + `derived_orderings()` — **80 orderings across 33 tables** | live |
| "do not run this" enforcement | `cedar_pipeline.guard()` / `NEVER_RUN` (4 scripts), enforced in code not comment | live |
| build entry point per dataset | `code/build.py plan|run|ship` — 12 collections + entity layer | live |
| machine-readable dataset inventory | `docs/ARCHITECTURE.md` + `docs/schema/dependency_manifest.json` (401 KB), both generated | live |
| identity model documentation | `docs/IDENTIFIER_STANDARD.md` (policy) + `docs/NATIVE_ENTITY_NUANCES.md` (domain) | live |
| canonical id stability | `cedar_uid`, meaning-free, 2 check chars, **100% substitution / 100% transposition** caught, deterministic re-mint verified by identical register digest | live |
| id materialised on every dataset | `503_identity.py stamp` — **125 tables, 3,007,088 rows (100.0%)** | live |
| release/regression gate | `62_no_regression_check.py` — ratcheted metrics, `MUST_BE_ZERO` / `MUST_NOT_RISE`, non-zero exit | live |
| failure-pattern detection | `293_lint_bug_classes.py` — **7 classes, 147 unwaived**, waivers counted and named | live |
| retirement with history | `graveyard/<date>_<reason>/GRAVEYARD_INDEX.md`, nothing deleted | live |

### F-2.1 The spec's failure-pattern list maps onto 293 more than it differs

**OBSERVED**, current counts:

| spec pattern | 293 class | count |
|---|---|---:|
| id minted from outside the row (process hash, rank, position) | **class7** | 42 |
| full rebuild silently reverting an in-place enricher | class6 | 30 |
| a drop counter that never names what it dropped | class2c | 60 |
| a per-unit budget that truncates and still marks COMPLETE | class4 | 9 |
| an "already done" short-circuit that rewrites its own log | class5 | 6 |
| a RULED method read as a positive ruling | class3 | 0 |
| reading staging/additions instead of the promoted table | class1 | 0 |

**INFERENCE:** Phase 6's release gate should add the spec's *missing* checks to
`62`/`293` as new ratcheted metrics — not stand up a second command system.
Missing today: undeclared many-to-many joins, orphaned canonical references,
lineage coverage, reconciliation-cycle detection, agent-task-cycle detection.

### F-2.2 Two non-determinism findings, both already triaged benign

**OBSERVED — I ran the spec's searches and inspected every hit.**

- `143_build_gaming_property_locations.py:376` — `uuid.uuid4().hex` is an **HTTP
  multipart form boundary** for the Census batch geocoder. It carries a
  `# lint-ok: class7` waiver stating a deterministic value would be the defect
  here, and nothing about it reaches a row. **Not a finding.**
- `227_anomaly_sweep.py:1038` — `hash(tuple(...))` is an **in-memory duplicate
  set** inside one process, never persisted. **Not a finding.**
- `code/cedar_keys.py` exists specifically to forbid this class, and
  `284_audit_nondeterministic_keys.py` measures it (`ferc_filing_id` was
  `abs(hash(...)) % 10000`; **4 of 2,534 ids stable across builds**).

**So the spec's headline id-instability risk is already detected, measured and
documented here.** It is not yet *fixed* for `ferc_filing_id`.

---

## F-3. RANKED FINDINGS

Ranked by the spec's criteria. "Blast radius" is what breaks if it goes wrong.

| # | finding | severity | likelihood | blast radius | detection difficulty | migration cost |
|---|---|---|---|---|---|---|
| ~~1~~ | ~~**No assertion layer; facts overwritten** (F-1)~~ **BUILT 2026-08-29** — `code/510_assertions.py`, `docs/ASSERTION_LAYER.md` | ~~critical~~ | — | 23,310 assertions, 22,984 resolved facts, 331 refutations carried | now visible: every losing value is written to `cedar_fact_conflicts.csv` | done |
| 2 | **No `lineage_root_id`; self-confirmation possible** (F-1.1) | critical | unknown, UNVERIFIED | any claim resting on "two sources agree" | very high — looks like corroboration | medium |
| 3 | **Registry and datasets in different trees** (F-0.1) | high | certain | the unregistered-source-id gate cannot exist | low, once stated | low (option a) |
| ~~4~~ | ~~**No commit substrate for the dataset tree** (F-0.2)~~ **RESOLVED** `2036e46` | ~~high~~ | — | code side now covered; data side still needs `run_id` + checksums | done | — |
| 5 | `ferc_filing_id` non-deterministic, **4/2,534 stable** | high | certain | any join on that id; nothing keys on it *yet* | already measured | low |
| 6 | Undeclared many-to-many joins unguarded | high | unknown | silent row multiplication in any build | high | medium |
| 7 | No agent-task dependency graph or handoff schema | medium | certain | duplicated work, unverifiable "done" | low | low |
| 8 | 3 tables still undocumented in the codebook | medium | certain | those 3 cannot ship | already gated | low |
| 9 | `docs/DOC_CONTRADICTIONS_2026-08-26.md` not re-run since today's changes | medium | certain | stale arbiter of conflicting numbers | low | low |

---

## F-1b. PHASES 1 AND 6, DELIVERED (added 2026-08-30)

**Phase 1 — dataset contracts.** `code/512_build_dataset_contracts.py`
generates `docs/schema/dataset_contracts.json` + `docs/DATASET_CONTRACTS.md`:
13 collections, 255 tables, each with status (shippable / internal / licensed /
undocumented), join keys, rebuilder, enrichers, NEVER_RUN warnings, and grain —
**declared only where an owner ruling or build log stated it; unstated grain is
recorded as unstated, never guessed.** Everything else is derived from the
systems that own the facts (500's collections, the codebook registry, the
pipeline's io map), because hand-maintained registries have already failed
here three times. First run found **28 orphan shippable tables** — shipping
with no owning collection — now all assigned; `contract_violations` and
`contract_orphan_shippable` gate at MUST_BE_ZERO in 62.

**Phase 6 — release gates, the half git enables.** `build.py ship --execute`
now refuses a dirty tree ("a release must point at a commit hash that actually
contains the code that built it") and stamps `docs/RELEASE_STAMP.json` with the
commit on success. Proven by firing: its first invocation refused to ship its
own uncommitted edit. Still open on Phase 6: replaying a *previous* release
end-to-end has never been demonstrated — the stamp records what would be
needed, it does not prove the replay works.

**Phase 4 — handoffs (added same day).** `code/513_handoffs.py`: a handoff is
a ROW born UNVERIFIED, carrying the commit hash, the touched tables' row
counts, and `verify_commands` — the exact commands whose exit 0 constitutes
proof. `verify` RE-EXECUTES them (it does not read the claim and nod), records
who/when/at-what-commit, and **refuses self-verification** — proven by firing
on its first recorded handoff. A disproven claim gates at MUST_BE_ZERO
(`handoffs_failed_verification`); the unverified queue is a note.

**Phase 5 — gaming pilot slice (added same day).** `gaming_source_claims` went
from contributing 0 assertions to 10/113 — identity attaches AT HARVEST through
the 503 resolver, never written back into the claims table, which stays the
verbatim record. The 103 unresolved are banks and non-Native counterparties,
unresolved BY DESIGN; the table's own recorded refusals are honoured, not
re-litigated.

**Phase 6 replay — the verification half, demonstrated 2026-08-30.**
Procedure, reproducible by anyone: `git worktree add <tmp> 98986ab`, junction
`data/clean` into the worktree read-only, copy the small spine CSVs, run the
commit's own `510 verify` and `512 verify`. Result: both pass with numbers
identical to the live run (29,726 assertions / 29,363 facts / 332 refutations;
13 collections / 255 tables / 0 violations), and the tracked identity register
is byte-identical between git's copy and disk (sha256 match). What this proves:
the code at a stamped commit runs and validates against the data. What it does
NOT prove, stated plainly: a full BUILD replay — rebuilding dist/ from raw at
that commit and matching digests — has still never been demonstrated, and the
run-manifest checksums remain the only attestation of the data side.

Remaining: Phase 5 at full breadth (the slice proves the stack; the gaming
collection's tables have not each been walked through it), Phase 7 (dataset
migration), and the Phase 6 BUILD-replay proof.

---

## F-3b. WHAT PHASE 3 MEASURED (added 2026-08-29)

The assertion layer is built and its gate is green. The result it produced
matters more than the machinery, and it is not the result that was expected.

**Every fact in Cedar rests on exactly one source.** Over 8,975 single-valued
facts: **0** have more than one source weighing in, **0** genuine
disagreements exist, and **2** have more than one independent evidence family —
the same 2 rows that already carried `TWO_INDEPENDENT_FEDERAL_SOURCES`.

So the arbitration layer currently has nothing to arbitrate. That is not a
failure of the layer; it is the layer doing the one job that had to come first,
which is making the state of the evidence base **measurable**. Before it, the
claim "Cedar overwrites facts" was an inference from the schema. It is now a
number.

Two things follow, and they reorder the remaining work:

1. **The next real task is a second independent source, not more machinery.**
   Harvesting the Federal Register roster directly was tried first: 565 of 575
   entries matched the spine and the corroborated-fact count stayed at **2** —
   correctly, because a copy of the FR living in the spine and the FR itself
   are the same evidence family. The lineage model works. What is missing is a
   source that is genuinely *elsewhere*.
2. **A ratchet that punishes correct classification was found and fixed.**
   Registering the three new tables as internal-by-decision raised four
   `tables_missing_from_*` counters by three apiece. `62` skipped licensed
   files from those counts but not internal ones. Making it consistent dropped
   `ship_tables_at_zero` 68 → 13 and `tables_missing_from_25_TABLES` 234 → 179:
   55 of the tables those metrics were reporting as unregistered had been
   correctly classified all along.

Also surfaced, pre-existing and still open: **`ANRC-BRBYCO-00` (Bristol Bay
Native Corporation) is keyed to "BRISTOL BAY AREA HEALTH CORPORATION" across
742 rows in 9 tables** (`FA-01`, informational in `62`, not gating). These are
different entities. It is exactly the class of error the assertion layer is
built to expose, and a good first test once a second source exists.

---

## F-4. WHAT PHASE 0 DID **NOT** ESTABLISH

Stated plainly, because the spec forbids claiming unverified behaviour.

- **UNVERIFIED:** whether any dataset can be rebuilt from a clean state.
  `build.py run --execute` has never been executed for any collection.
- **UNVERIFIED:** determinism of any dataset build. The only determinism proven
  today is the **identity register** (identical digest on re-mint) — not a build.
- **UNVERIFIED:** whether a previous release can be reproduced. `dist/` holds
  one CSV; the shipping chain has never been run end to end.
- **UNVERIFIED:** actual vs declared row grain per dataset. The spec requires
  both; only declared grain exists, in `docs/datasets/*.md` and the codebook.
- **NOT DONE:** the per-dataset trace table (source registration → … →
  publication) for all 12. `docs/ARCHITECTURE.md` has the tables-and-scripts
  half; the source-acquisition and snapshot half is not machine-readable.
- **NOT DONE:** the three directed graphs as *separate* artifacts. Pipeline
  dependencies exist (80 orderings); identity and agent-task graphs do not.

## F-5. RECOMMENDED SEQUENCE, GIVEN THE ABOVE

The spec's own escape clause applies: this is more than one session. Proposed
order, smallest blocking thing first:

1. **F-0.1** — vendor `sources.jsonl` + `schema/` into Cedar Press with a
   checksum and staleness gate. Unblocks the unregistered-source-id gate, which
   several later phases depend on. Low cost, reversible.
2. ~~**F-0.2**~~ — **done for the code side** (`git init`, commit `2036e46`). The run
   manifest with `run_id` + `code_version` + logical checksums is still needed
   for the **data** side, which no commit hash can attest to.
3. **Phase 3 first, not Phase 1** — the assertion layer (F-1, F-2) is the
   critical finding and the thing that gets harder every day the current
   overwrite behaviour continues. Extend `cedar_identifier_ledger`'s proven
   model to non-identifier fields rather than inventing one.
4. Phase 1 contracts, Phase 2 identity formalisation (largely written already),
   Phase 4 agent protocol, then the Phase 5 gaming pilot.

**Deliberately not started:** any refactor. Phase 0 forbids it, and findings 1
and 2 would change the shape of any refactor done before them.
