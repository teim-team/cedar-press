# Release replay log

*Workstream C, 2026-08-29. External review finding **F13**, ADR-004. This
document is the evidence for one claim and the refutation of a larger one.*

> **Superseded in part.** Part I below is the record of the first clean-room
> replay, and its findings stand as written for the state of the tree on
> 2026-08-30. Two of its statements are no longer true and are corrected in
> **Part II** (workstream G, 2026-08-29, commit `6c92a41`): §8's *"no table in
> this release is byte-identical on replay"* — four now are — and §5's B4,
> which is fixed for `nagpra`. Read part I for the method and part II for the
> current numbers.

**The claim being tested.** *Given a Cedar release identifier, we can identify
and retrieve the exact transitive inputs, code, configuration, environment and
manual decisions needed to reproduce the released outputs — or explicitly state
which component prevents exact reproduction.*

**Result.** A real clean-room replay was performed on the `nagpra` collection at
commit `0de7096`. Every input was retrieved from a retained immutable store and
nothing was read from the live tree. Two of the four tables reproduced
**exactly, row for row, on every column the pipeline computes**. Two did not,
and both failures have a named cause that the manifest now detects *before*
anyone runs a replay.

**Commercial-release condition — "a release successfully replayed from retained
immutable inputs" — is PARTIALLY MET.** The retention half is met and proven.
The exact-reproduction half is not, for four named reasons listed in §5.

---

## 1. What was wrong with the previous answer

The 2026-08-30 drill (`docs/FOUNDATION_AUDIT.md`, F-1b) checked out a commit,
pointed it at **today's** `data/clean` through a junction, and ran `510 verify`
and `512 verify`. Both passed. What that proved is real and narrow: *the code at
a stamped commit runs and validates*.

It did not prove the release could be rebuilt, because:

- the data it validated against was the **live tree**, not the release's data;
- nothing was retained, so there was nothing to rebuild *from*;
- no output was compared to anything.

`27_build_dataset_manifests.py` records input sha256s. The reviewer's sentence
is the whole objection: **a checksum is a receipt, not a backup.** A hash proves
a new download differs. It hands nobody the file we shipped.

## 2. What was built

`code/516_release_manifest.py`. One script, five commands:

```
py -3 code/516_release_manifest.py build --collection nagpra   # or --all
py -3 code/516_release_manifest.py verify   [--release <id>]
py -3 code/516_release_manifest.py replay   --release <id> --into <dir>
py -3 code/516_release_manifest.py compare  --release <id> --replay-root <dir>
py -3 code/516_release_manifest.py list
```

It is wired into `code/build.py` as **post-chain step 8** of `ship --execute`
(after the runbook's seven, so the documented "7-step chain" stays true), and
`docs/RELEASE_STAMP.json` now carries `release_id`, `release_manifest` and
`replayability_verdict` beside the commit.

### What the manifest captures

| F13 requirement | where it lands | how it is derived |
|---|---|---|
| commit | `commit`, and **per script** `matches_commit` | working blob vs `HEAD:code/<s>` |
| every consumed input, transitively | `collections[].inputs[]` | three channels — see below |
| content hashes | `sha256` per file; `tree_sha256` (merkle) per directory | full read |
| **retained immutable location** | `retention.blob` under `data/_release_inputs/blobs/` | content-addressed copy, read back and re-hashed before it is trusted |
| source snapshot / retrieval | `provenance` | `data/raw/**/_SOURCE_MANIFEST.csv` → fetch stage in code → hand-coded → producing Cedar collection |
| dependency / environment lock | `environment` | interpreter, platform, `pip freeze` + its own sha256 |
| configuration | `configuration` | frozen seeds and tunables read off the scripts (e.g. 78's `AUDIT_SEED = 20260806`) |
| commands executed | `commands` | ordered argv, with the `build` sub-stage detected for staged scripts |
| manual verification / adjudication inputs | `manual_decision_inputs` | anything under `review/`, or named `*rulings*` / `*verdict*` / `content_audit_*` |
| output schema | `outputs[].columns` | header read |
| primary keys | `outputs[].primary_key` + `primary_key_evidence` | `docs/schema/keys.json` |
| output hashes | `outputs[].sha256` | full read |
| row counts + conservation | `outputs[].rows`, `outputs[].conservation` | full scan; distinct/blank counts on `document_number`, `cedar_uid`, `tribe_id` |

### Input discovery uses three channels, because one is provably not enough

1. **`cedar_pipeline.declared_io()`** — the project's own io scanner, the same
   one `287_build_dependency_manifest.py` is built on.
2. **A module-level path-constant walk** (AST) that resolves
   `CEDAR / "data" / "raw" / …` chains.
3. **The import closure** — 77 resolves entities through
   `33_apply_party_rulings`, so 33's reads are 77's reads.

Channel 1 alone reports NAGPRA's inputs as
`cedar_entity_spine.csv, federal_actions.csv`. It **misses
`data/raw/federal_register/nagpra_fulltext/`** — the 18.2 MB, 6,700-file gz
cache the entire dataset is parsed out of — because it reports *filenames* and
that input is a directory built from path constants. It also misses
`native_bills.csv` (reported as `unknown`). Channel 2 catches both. A manifest
inheriting channel 1's blind spot would have certified this release as fully
captured while its largest substantive input went unrecorded.

Names the io scanner cannot classify inside a module that is only **imported**
(`cedar_domain.py` is a registry of table names, so it looks like fifteen reads
and opens nothing) are recorded as `io_scan_unresolved_names` — informational.
Names an **executed** script reads that no channel resolves are
`undiscovered_inputs` — blocking. For `nagpra`, `undiscovered_inputs` is **0**.

### Retention policy, and its honest limit

`data/` is ~46 GB; some inputs live outside it. Retaining everything is a wish,
not a policy. So:

- files ≤ `RETAIN_MAX_BYTES` (512 MiB) are **copied** into
  `data/_release_inputs/blobs/<aa>/<sha256><ext>`, deduplicated by content
  across every release that uses them — the second release consuming the same
  255 MB `federal_actions.csv` costs zero additional bytes;
- directory inputs are retained as one deterministic zip named by the tree's
  **merkle root**, not by the zip's own hash (zip byte order is not stable);
- anything larger is `referenced_only`: hash + provenance + a named retrieval
  procedure, and the release is marked not exactly replayable, naming it;
- every copy is **read back and re-hashed** before it is called retained, and
  the blob is then set read-only. Restored inputs inherit that mode, so a
  clean room physically cannot mutate what it was given. The trade-off is
  real and named: a collection whose plan includes an enricher that rewrites
  an *input* in place will fail in the clean room until that file is
  re-flagged writable — and that failure is information, because such a
  collection has no from-scratch build path.

For `nagpra`: **8 of 8 inputs retained, 296 MB in the store**, 0 referenced-only.
`verify` re-hashes every blob and exits 0.

**Proven by firing, not by reading the code.** Appending one byte to a retained
blob makes `verify` exit **1** with
`BLOB CONTENT DRIFT … 68823638ab39 != bc20de61c1cf` and
`retained_verified 7 … drift 1`; restoring the file returns exit **0** and
`retained_verified 8 … drift 0`. A store nobody can prove is intact is a store
nobody should trust.

Dedup measured rather than asserted: capturing a second release over the same
inputs moved the store from **296,266,471 bytes to 296,266,471 bytes** — delta
**0**, with all 8 inputs flagged `deduplicated: true`. The cost of retaining a
release is the bytes it introduces, not the bytes it consumes.

**Where each half lives, and why.** The blob store is `data/_release_inputs/`,
which `.gitignore`'s `/data/*` rule excludes — content stays out of git, exactly
as the rest of `data/` does, and is retired by MOVE to `graveyard/` like
everything else. The manifest is `docs/releases/<id>/manifest.json`, which git
**does** track, because the receipt for a release has to survive in the same
history as the code it names. A manifest whose blobs have been moved to
`graveyard/` still says what the release consumed and where it went; that is
the difference between an archive and an amnesia.

---

## 3. The replay — reproducible by a human, step by step

Live tree untouched throughout; all work in a scratch worktree.

```
# 0. from the repo root, on a quiescent tree
cd "C:\Users\esm247\Desktop\Cedar Press"

# 1. capture the release: hash, retain, and record everything
py -3 code/516_release_manifest.py build --collection nagpra --release nagpra-0de7096

# 2. prove the retained store is intact
py -3 code/516_release_manifest.py verify --release nagpra-0de7096     # exit 0

# 3. materialise a clean room: git worktree at the commit, plus ONLY the
#    inputs the manifest names, restored from the blob store
py -3 code/516_release_manifest.py replay --release nagpra-0de7096 --into <scratch>\replay_nagpra

# 4. run the release's own commands, inside the clean room
cd <scratch>\replay_nagpra
py -3 code/77_build_nagpra_dataset.py build
py -3 code/78_content_analysis.py

# 5. compare outputs, schemas, primary keys and row counts
cd "C:\Users\esm247\Desktop\Cedar Press"
py -3 code/516_release_manifest.py compare --release nagpra-0de7096 --replay-root <scratch>\replay_nagpra

# 6. tear down
git worktree remove --force <scratch>\replay_nagpra
```

Step 3 restores **only** what the manifest names. If a script reaches for a
file that is not there, the manifest was wrong — the clean room is the test of
the manifest as much as of the code.

Step 3 also applies **adaptation A1** (below) and writes `adaptations.json`
recording the before/after sha256 of every file it touched.

**A note on doing this during a live pass.** `HEAD` moved from `fb8100b` to
`0de7096` while this drill was running — the integrator landed workstream A.
The first capture and its replay were therefore discarded and redone at the new
commit. That is the correct response, and the manifest is what makes it
detectable: it records the commit, and it records **per script** whether the
working blob matches the blob at that commit. All four scripts in NAGPRA's
scope are byte-identical across `fb8100b` and `0de7096`
(`git rev-parse <commit>:code/<script>`), so the discarded run would have given
the same answer — but "would have" is not evidence, so it was rerun.

## 4. The result, table by table

Both runs — `fb8100b` and `0de7096` — produced identical outputs (same row
counts, same file sizes, same content digests), which is a small determinism
check nobody asked for and worth having.

```
table                            verdict                          replay / released
fr_nagpra_title_index.csv        SUPERSET +38                       6,644 /  6,606
fr_nagpra_title_index_year.csv   DIFFERS_ROWS                          33 /     33
nagpra_notice_entity_bridge.csv  IDENTICAL_EXCEPT cedar_uid        51,521 / 51,521
nagpra_notices.csv               IDENTICAL_EXCEPT fetched_date      6,772 /  6,772
```

**`nagpra_notices.csv` — reproduced.** 6,772 rows both sides, schema identical,
primary key `document_number` unique with 0 blanks in the replay. All 66
columns agree on all 6,772 rows **except `fetched_date`**, which holds the
wall-clock date of whichever day the build ran (`2026-08-26` released,
`2026-08-29` replay). Digest over the other 65 columns: `fabe664de011d59b…` on
both sides.

**`nagpra_notice_entity_bridge.csv` — reproduced.** 51,521 rows both sides.
The released table has one extra column, `cedar_uid` (48,054 filled). On the
14 columns `77_build_nagpra_dataset.py` writes, the two files are identical —
0 differing cells across 51,521 rows.

**`fr_nagpra_title_index.csv` — NOT reproduced, and the release is why.** The
replay is a strict **superset**: all 6,606 released rows present, **0 of them
different**, plus 38 rows, all 2026 publications. The released file was written
`2026-08-06`; the `federal_actions.csv` the manifest records as its input was
written `2026-08-26`. The released bytes were never produced by the recorded
input. A faithful replay *cannot* reproduce them and should not be expected to.

**`fr_nagpra_title_index_year.csv` — NOT reproduced, downstream of the above.**
Identical key set, one row disagrees: 2026 counts 590 (replay) vs 552
(released) — the 38 documents above.

### 4b. The whole release, measured but not replayed

One collection was replayed. All thirteen were *captured*, so the shape of the
problem is now a number rather than an intuition:

```
py -3 code/516_release_manifest.py build --all --no-retain --release <id>
  13 collections   513 inputs   260 outputs        release verdict: not_exactly_replayable

blocking class                        collections
  output_stale_vs_input                    13/13
  undeclared_enricher                      13/13
  nondeterministic_output_column           13/13
  code_not_relocatable                     13/13
  input_changed_during_capture             13/13
  undiscovered_inputs                      11/13
  code_not_at_commit                        6/13
  plan_script_missing                       3/13
```

**Read that capture with its caveat, which the manifest states itself: it was
NOT quiescent.** Two inputs (`cedar_resolved_facts.csv`,
`_correction_scan_cache.json`) were rewritten by another workstream while the
sweep was running, so the manifest set `quiescent: false`, named both files,
and refused the release a clean verdict. That is the check working. It also
means the sweep's *per-table* staleness figure (260 of 260) is an artifact of
capturing a tree that four workstreams are writing — on a live tree something
is always newer than something. **A release capture must happen on a frozen
tree**, and that is now a procedure, not a preference.

What the sweep does support, because none of it depends on quiescence:

- **236 reads by executed scripts, across 11 collections, that no discovery
  channel could resolve to a file.** That is the honest size of the
  input-discovery gap — 8 collections' worth of inputs we cannot yet name, let
  alone retain. NAGPRA's 0 is the exception, not the rule.
- **284 run-stamp columns** across the 13 collections. `fetched_date` is not a
  quirk of one script.
- **`503_identity.py` writes 96 tables it is not planned to write**, followed
  by `327_migrate_class7_keys_to_digests.py` (23), `163_load_sam_contract_awards.py`
  (13), `102_build_coverage_profile.py` (13), `164_refresh_nho_review_queues.py`
  (13); 33 more backups are UNATTRIBUTED — a tag whose source line no longer
  exists.
- **3 collections plan a script that is not in the repository** (D7).

The sweep costs one command and no retention; it took roughly an hour of wall
clock on a contended machine, dominated by full CSV parses of a 1.0 GB and a
578 MB table. Its manifest was 2.4 MB and is deliberately **not** committed:
it is a dry run over a moving tree, and a receipt for a state that never held
still is not a receipt. Regenerate it rather than trusting a stored copy.

## 5. Every point where exact replay fails, with the blocking component named

The manifest computes these from the live tree, **before** a replay is run. It
found all four on `nagpra`, and the replay then confirmed all four.

### B1 — `code_not_relocatable`: the project root is hardcoded

**280 of 385 scripts in `code/`** (72.7%) contain
`Path(r"C:\Users\esm247\Desktop\Cedar Press")`. Three of them are in NAGPRA's
scope. A checkout at any other path therefore reads *and writes* the live tree,
which makes a clean room impossible without modifying the code.

**Adaptation A1** is the workaround the replay used: rewrite that single string
literal, per file, to the clean-room root; record before/after hashes in
`adaptations.json`. Mechanical, auditable, and it changes nothing else — but it
means the replayed code is **not byte-identical to the commit**, and the log
says so rather than pretending otherwise.

*Severity:* survivable-with-adaptation. *Gated debt:* **D1**, below.

### B2 — `output_stale_vs_input`: a released output predates a recorded input

`fr_nagpra_title_index.csv` and `fr_nagpra_title_index_year.csv` were last
written 2026-08-06; `federal_actions.csv` was rewritten 2026-08-26. This is not
a replay failure — it is the manifest catching a release that had already
drifted from its own inputs, and it was invisible before this pass.

Evidence is **mtime only**, and the manifest says so: a content-identical
rewrite moves an mtime without changing what a file says, so this can flag a
release that is in fact current. It stays blocking because the opposite error —
shipping a stale table as replayable — is the one that costs money.

*Severity:* fatal to exact replay. *Gated debt:* **D2**.

### B3 — `undeclared_enricher`: a script outside the plan wrote the output

`nagpra_notice_entity_bridge.csv` carries `cedar_uid` in the release and not in
the replay. The evidence is physical:
`nagpra_notice_entity_bridge.csv.bak_2026-08-28_pre505`, and `pre505` appears
verbatim in **`code/503_identity.py`**. 503 discovers its tables at runtime, so
no static io scan can attribute it, and `build.py`'s plan for `nagpra` therefore
lists **zero** phase-2 enrichers. The plan is incomplete, so the manifest's
command list is incomplete, so the replay cannot produce the released columns.

A second backup, `*.bak_2026-08-26_pre_342_nagpra_refresh`, attributes by
numeric tag to `342_pull_federal_register_incremental.py`, also outside the plan.

*Severity:* fatal to exact replay. *Gated debt:* **D3**. **This needs a change
in a file workstream C does not own** — see §7.

### B4 — `nondeterministic_output_column`: the clock is written into rows

`nagpra_notices.csv.fetched_date` holds one constant value: the day the build
ran. Two faithful runs on two days produce different bytes and always will.
The manifest lists such columns up front (a column whose every non-blank value
is a single ISO date), and `compare` sets exactly those aside and prints which
ones it set aside, every time, so the exclusion cannot quietly grow.

*Severity:* survivable-with-adaptation (compare with the column excluded).
*Gated debt:* **D4**.

### One thing the replay found that is not a replay problem

`compare` re-tests the declared primary key against the replayed table, and
`nagpra_notice_entity_bridge.csv`'s declared key in `docs/schema/keys.json` is
**14 columns** — effectively the whole row. It is distinct over 51,521 rows only
because a 14-column tuple always is, and 3,467 of those tuples carry a blank
component. That is not a key a buyer can join on; it is "the row is unique
because it is the row". Reported here rather than fixed: `keys.json` is produced
by `284_audit_nondeterministic_keys.py`, outside workstream C's files.

The same table's neighbour shows a second, quieter version of B2. `keys.json`
records `nagpra_notices.csv`'s key evidence as *"document_number: 6,729 distinct
over 6,729 rows"*. The table on disk has **6,772 rows**. The key claim is
therefore attested against a table that no longer exists, and the manifest
carries the evidence string verbatim so the discrepancy is visible rather than
laundered into a bare `"proven": true`.

### Not encountered here, but detected by the same machinery

- `input_not_retained` — an input too large for the retention policy. 0 for
  `nagpra`; expected to be non-zero for `contractors` / `funding`, whose raw
  dumps live in `Federal Spending/`.
- `undiscovered_inputs` — an executed script reads something no channel found.
  0 for `nagpra`.
- `code_not_at_commit` — a script in scope differs from the commit the release
  names. 0 for `nagpra` (the tree was dirty with other workstreams' files, and
  the manifest says precisely that: dirty tree, every script in scope
  byte-identical to `0de7096`).
- `input_changed_during_capture` — inputs are re-hashed at the end of `build`
  and any that moved are named. Four workstreams write this tree at once; a
  manifest hashed while an input was being rewritten describes a state that
  never existed. `nagpra` capture was quiescent.

---

## 6. What was fixed, and what is gated debt

### Fixed this pass

| | |
|---|---|
| Inputs are **retained**, not merely hashed | content-addressed store, deduplicated, read back and re-verified on write |
| Transitive input discovery | three channels; the directory corpus channel 1 misses is now captured |
| Provenance is a **named procedure**, per input | and it no longer over-reaches: an earlier version labelled `cedar_entity_spine.csv` as retrievable from federalregister.gov, which would have handed a replayer the wrong file with no warning |
| Replay is one command | `replay` builds the clean room; `compare` grades it |
| A hash mismatch now says **why** | run-stamp columns, enricher columns, key-set relation, first differing cells |
| Staleness is detectable without a replay | B2 above; it found a real one on its first run |
| Undeclared enrichers are detectable | B3 above, from the enrichers' own backup files |
| Capture integrity | inputs re-hashed at the end; a non-quiescent capture is refused a clean verdict |
| The verdict is **computed and tiered** | `exactly_replayable` / `replayable_with_named_adaptations` / `not_exactly_replayable`; never asserted |
| The ship chain records it | `build.py` step 8; `RELEASE_STAMP.json` carries the verdict |

### Gated debt — named, measurable, and not vague

| id | debt | measure today | target | gate |
|---|---|---|---|---|
| **D1** | Project root hardcoded, so no script can run outside `C:\Users\esm247\Desktop\Cedar Press` | **280 of 385** scripts (72.7%) contain the literal | 0; root derived as `Path(__file__).resolve().parent.parent` | `scripts_with_hardcoded_root`, **MUST_NOT_RISE**, ratchet to 0 |
| **D2** | Outputs shipped that predate their recorded inputs | **2 of 4** NAGPRA tables, proven by replay. The release-wide figure needs a frozen tree; the live sweep flags 260/260 and is not usable (see 4b) | 0 | `release_outputs_stale_vs_input`, **MUST_BE_ZERO**, measured on a frozen capture |
| **D3** | Runtime-dispatch enrichers invisible to the build plan, so no plan reproduces the released columns | **13/13 collections.** `503_identity.py` writes **96** tables it is not planned to write; 327 writes 23; 33 backups are UNATTRIBUTED. `build.py plan nagpra` reports 0 phase-2 enrichers for a table 503 demonstrably edited | every writer of a shipped table appears in that collection's plan | `undeclared_enrichers`, **MUST_BE_ZERO** |
| **D4** | Wall-clock written into output rows | **284 columns across 13/13 collections**; `nagpra_notices.fetched_date` is the one proven by replay | 0, or the column derives from the source's own date | `nondeterministic_output_columns`, **MUST_NOT_RISE**, ratchet down |
| **D5** | Only 1 of 13 collections has been REPLAYED (all 13 are captured) | 1/13 replayed, 4/260 tables | 13/13 | `collections_never_replayed`, **MUST_NOT_RISE** |
| **D6** | Retention untested at scale; large raw inputs will be `referenced_only` | 296 MB retained for 1 collection (8/8 inputs). The other 12 declare **513 inputs** in total and have never been retained | a measured per-release retained/referenced split for all 13 | `release_inputs_referenced_only`, reported per release |
| **D7** | A collection's build plan names a script that is not in the repository, so its documented rebuild command cannot run end to end | **3 collections**: `deals` → `build_v2.py`, `lobbying` → `05_match_filings_v2.py`, `natural-resources` → `update_index.py` | 0 | `plan_scripts_missing`, **MUST_BE_ZERO** |
| **D8** | Input discovery cannot resolve every read an executed script makes | **236 unresolved reads across 11 of 13 collections** (NAGPRA: 0) | 0 — every read resolves to a named, retained or explicitly referenced-only input | `undiscovered_inputs`, **MUST_NOT_RISE**, ratchet to 0 |
| **D9** | A release capture is only valid on a frozen tree, and nothing enforces the freeze | the 13-collection sweep had **2 inputs rewritten under it** by a concurrent workstream | a declared freeze window, or `ship --execute` refusing while another writer is live | `release_captures_non_quiescent`, **MUST_BE_ZERO** |

D1–D9 are stated here rather than added to `62_no_regression_check.py`, which
workstream D owns this pass. Wiring them is a one-line-per-metric change and is
requested in the handoff.

D7 is the cheapest of the seven and the most embarrassing: three of the
thirteen `py -3 code/build.py run <collection> --execute` commands printed in
`docs/DATASET_CONTRACTS.md` end in a `FileNotFoundError`. The io map is built
from a scan whose record outlives the file it recorded. Nothing had ever tried
to execute the plans it produces, so nothing had noticed.

## 7. Changes needed in files workstream C does not own

1. **`code/62_no_regression_check.py` (workstream D)** — register D1–D6 above as
   gate metrics. D1 (`scripts_with_hardcoded_root`, currently 280) and D3
   (`undeclared_enrichers`) are the two that would have caught this class of
   defect years of releases ago.
2. **`code/503_identity.py` (workstream D)** — it stamps `cedar_uid` into
   tables it discovers at runtime, which is why no plan and no static scan can
   see it. It should either (a) write the list of tables it touched to a
   machine-readable run record that `build.py` and 516 can read, or (b) declare
   its table set. Option (a) is smaller and does not constrain what 503 may do.
   **Not editing it was correct this pass; it is D's file.**
3. **`docs/SHIPPING_RUNBOOK.md`** (unclaimed) — part 1 should mention the
   post-chain step 8 and that `RELEASE_STAMP.json` now carries
   `replayability_verdict`. Left unedited to avoid a racing edit.
4. **`code/77_build_nagpra_dataset.py`** (unclaimed, but out of C's scope) —
   `fetched_date` should record the date the *cached document* was fetched, not
   `date.today()` at build time. That single change makes `nagpra_notices.csv`
   byte-reproducible.
5. **A freeze window, owned by the integrator.** During this pass `62` returned
   exit 0, then 1 on `sem_entities_uid_reassigned`, then 0, then 1 on three
   `sem_facts_*` ceilings, then 1 on `sem_entities_uid_reassigned` again, then
   0 — while `cedar_resolved_facts.csv` and `cedar_identity_register.csv` were
   rewritten underneath it by workstream D. Named in `AGENTS.md` per standing
   rule 15 option 3. This is the same defect as **D9**: both the gate and a
   release capture assume one writer, and the parallel pass broke that
   assumption without anyone deciding to. A release captured on a moving tree
   is a receipt for a state that never held still.

## 8. Verdict, stated plainly

**Commercial-release condition "a release successfully replayed from retained
immutable inputs": PARTIALLY MET.**

Met and proven:

- inputs are retained immutably, content-addressed, verified on write and
  re-verifiable on demand (`verify` exits 0 over 8/8 NAGPRA inputs);
- a clean room can be built from the store alone, with nothing read from the
  live tree;
- a real replay ran and **reproduced 2 of 4 tables exactly on every column the
  pipeline computes** — 6,772 and 51,521 rows respectively, primary keys
  holding, schemas matching;
- for the 2 that did not reproduce, the blocking component is named, and one of
  them (B2) is a defect *in the release*, not in the replay.

Not met:

- **no table in this release is byte-identical on replay.** Four named
  obstacles (B1–B4) stand between "reproduced the content" and "reproduced the
  bytes";
- **12 of 13 collections have never been replayed.** All 13 are now *captured*,
  which is how we know the gap's size — 236 unresolvable reads, 284 run-stamp
  columns, 96 tables written by one unplanned enricher — but a capture is a
  description of the problem, not a solution to it;
- **no release capture has yet been taken on a frozen tree.** The 13-collection
  sweep had two inputs rewritten under it mid-run. The manifest caught it and
  refused a clean verdict; nothing yet prevents it;
- the collections with multi-GB raw inputs will hit `referenced_only`
  retention, which the policy permits and the verdict will refuse to call
  exactly replayable.

"It ran" is not "it reproduced", and "it reproduced the content" is not "it
reproduced the release". This document is written so nobody has to guess which
one we mean.

---

# Part II — replay breadth (workstream G, 2026-08-29, commit `6c92a41`)

*Part I above is workstream C's account of the first clean-room replay. This
part extends coverage from one collection to four, re-tests the one C replayed
after its blocking B4 column was fixed, and closes D9 for the captures it
took. It also records two defects in `516` itself, one live-tree incident, and
two new debts, because a replay log that records only the pipeline's faults is
advocacy rather than evidence.*

**Headline.** `nagpra_notices.csv` and `nagpra_notice_entity_bridge.csv` are
now **BYTE-IDENTICAL on replay** — 6,772 and 51,521 rows, sha256 equal on both
sides. Part I's closing sentence, *"no table in this release is byte-identical
on replay"*, is **superseded**: four tables across two collections now are.

## 9. What was replayed, and what it produced

Four collections captured at `6c92a41`, all four **quiescent**, all inputs
retained and re-verified, all four clean rooms built from the blob store alone.
25 tables compared. Every verdict below is computed by `516 compare`, never
asserted.

```
collection                inputs retained   tables   byte-identical   artefacts
nagpra                       8 / 8            4          2            docs/releases/nagpra-6c92a41/
subcontracting              20 / 20           5          2            docs/releases/subcontracting-6c92a41/
natural-resources           44 / 44           9          0            docs/releases/natural-resources-6c92a41/
native-owned-businesses      4 / 4            7          0            docs/releases/native-owned-businesses-6c92a41/
                                             --         --
                                             25          4
```

**Why these three.** Chosen on measured input footprint, smallest first, using
the new `516 survey` (which needs no hashing and no CSV parsing). At the time
of choosing, subcontracting was the smallest collection in the release at
64.5 MB, natural-resources second at 430 MB, native-owned-businesses third at
816 MB. Two of those numbers were wrong, and finding out why is §11:
subcontracting is really 1,882 MB once discovery can see `os.path.join`. The
survey is kept as `docs/releases/_analysis/collection_survey.json`.

### 9a. `nagpra` — B4 is fixed, and the fix is proven by bytes

```
table                            verdict                    replay / released
nagpra_notices.csv               BYTE_IDENTICAL               6,772 /  6,772
nagpra_notice_entity_bridge.csv  BYTE_IDENTICAL              51,521 / 51,521
fr_nagpra_title_index.csv        SUPERSET +38                 6,644 /  6,606
fr_nagpra_title_index_year.csv   DIFFERS_ROWS                    33 /     33
```

`nagpra_notices.csv` was `IDENTICAL_EXCEPT fetched_date` in part I. Since then
`77_build_nagpra_dataset.py` gained `cache_fetched_date()`, which reads the
date off the **cached artifact** and returns `""` when the artifact cannot say,
instead of `date.today()`. sha256 `e6cc77950c62…` on both sides, all 66
columns, all 6,772 rows. The `nondeterministic_output_column` blocker no longer
appears for this collection at all: its run-stamp count is **0**, the only zero
in the release (§12).

Run twice, on two separate captures and two separate clean rooms, with the same
result.

`nagpra_notice_entity_bridge.csv` reproduced byte-identically for a different
and less comfortable reason. In part I the released copy carried an extra
`cedar_uid` column that `503_identity.py` had stamped in. The released table
today has 14 columns and no `cedar_uid` — a rebuild since 503 last ran dropped
it. The bytes match because **the enricher's work is currently absent from the
release**, not because the plan now reproduces it. B3 is still live and still
blocking: the manifest raises `undeclared_enricher` on this collection from the
`.bak_…_pre505` evidence, and the day 503 runs again this table stops
reproducing.

The two `fr_nagpra_title_index*` tables fail exactly as in part I, unchanged:
**B2**, a released output written 2026-08-06 from a `federal_actions.csv`
rewritten 2026-08-26. All 6,606 released rows are present and identical in the
replay, which adds 38 rows of 2026 publications the released file could not
have seen. A faithful replay cannot reproduce a table its recorded input never
produced.

### 9b. `subcontracting` — 2 of 5, and a live API call inside a build plan

```
prime_sub_network.csv            BYTE_IDENTICAL                 220 /    220
subaward_identifier_harvest.csv  BYTE_IDENTICAL                 304 /    304
subaward_identifier_netnew.csv   DIFFERS_ROWS (subset, -17)     193 /    210
subaward_entity_rollup.csv       DIFFERS_SCHEMA                 507 /    450
subawards.csv                    DIFFERS_SCHEMA              56,817 / 72,837
```

Two tables reproduce to the byte. The other three fail for one reason with a
name: **`121_pull_subawards_api.py` is a phase-2 enricher in this collection's
plan and it fetches from `api.usaspending.gov` at build time.** In the clean
room it downloaded fy2021 (765,109 rows) and **failed on 4 of its 5 fiscal
years**, because the cached download tokens the release used have expired at
the source. The 16,020-row shortfall in `subawards.csv` is those four years;
`subaward_entity_rollup.csv` is downstream of it.

This is a class of blocker the manifest could not previously state, and it is
worse than a missing file: **a release whose build plan performs a live API
call has, as one of its inputs, the internet on the day it ran.** Retention
cannot hold that and no threshold change makes it retainable. Recorded as
**D10**.

`250_demote_stale_tierA_subaward_rows.py`, also in the plan, could not run at
all: it requires `review/ancsa_tierA_subaward_disposition_<TODAY>.csv`,
produced by `249`, which is not in the plan. A filename containing today's date
can never be an input to yesterday's release.

The four columns `compare` set aside for `subawards.csv` — `cedar_uid`,
`deflator_factor_2025`, `inflation_base_year`, `subaward_amount_real2025` —
are all written by scripts outside this collection's plan, which is B3 again in
a second collection.

### 9c. `natural-resources` — 0 of 9, and D7 confirmed by execution

```
anc_ceiling_roster.csv             IDENTICAL_EXCEPT fetched_date   196 /    196
nd_severance_allocation.csv        DIFFERS_SCHEMA                    7 /      7
resource_revenue.csv               DIFFERS_SCHEMA                9,562 / 10,482
resource_parties.csv               DIFFERS_SCHEMA                  118 /  1,436
tribal_tax_bases.csv               DIFFERS_SCHEMA                   96 /  1,712
resource_assets.csv                DIFFERS_SCHEMA                    0 /     35
ancsa_filings_index.csv            NOT_PRODUCED                      - / 19,269
resource_asset_source_coverage.csv NOT_PRODUCED                      - /     18
tribal_bond_issuances.csv          NOT_PRODUCED                      - /     29
```

Nothing reproduces. One table, `anc_ceiling_roster.csv`, is identical on all
196 rows once `fetched_date` is set aside — a D4 column, one line from
reproducible by the pattern 77 now demonstrates.

**D7 is confirmed by execution, not inspection.** The plan's sixth command is
`py -3 code/update_index.py`, and in the clean room it produced
`can't open file … code\update_index.py: [Errno 2] No such file or directory`.
The rebuild command printed in `docs/DATASET_CONTRACTS.md` for this collection
does not run.

Three of the nine tables have **no writer in the plan at all**.
`resource_asset_source_coverage.csv` is written by
`135_build_resource_assets.py`, which `build.py` classifies AMBIGUOUS
(rebuilder for one table, enricher for two others) and therefore omits. A table
nobody plans to write is a table nobody can replay. Recorded as **D11**.

The row shortfalls are input discovery, and they are the honest size of D8:
`tribal_tax_bases.csv` replayed 96 rows against a released 1,712 because
`108_build_tribal_tax_bases.py` enumerates its sources at runtime out of a
`_SOURCE_MANIFEST.csv`. 516 now reads those manifests (§11), which moved this
table from 24 replayed rows to 96. The remaining gap is real and unclosed.

### 9d. `native-owned-businesses` — 0 of 7, and the reason is structural

All seven tables `NOT_PRODUCED`. This collection's plan contains **zero phase-1
rebuilders**; its single planned command,
`242_build_individual_native_firm_contracts.py`, aborts on its first check:

```
ABORT: individual_native_firm_register.csv is empty or missing. Run code/241 first.
```

`241_promote_individual_native_firms_in_place.py` is AMBIGUOUS, so it is not in
the plan. Running it as a named adaptation did not rescue the replay either: in
a correctly sealed clean room 241 aborts on *its* required inputs, which the
manifest never named because 241 is not in scope, so its reads were never
discovered. **This collection has no from-scratch build path at all**, and that
is a fact about the release, not about the replay.

Its one substantive input, `data/clean/prime_contracts.csv` (815,967,130 B),
exceeds the default `RETAIN_MAX_BYTES` of 512 MiB. Captured at the default it is
`referenced_only` and the release is additionally blocked on
`input_not_retained` — that capture was taken and the blocker observed. The
release filed here raised `--retain-max` to 1 GiB and retained it, so that one
blocker is discharged and the threshold in force is recorded in the manifest.
**Two releases captured under different thresholds are not silently
comparable.** The thresholds used were 512 MiB (nagpra, natural-resources),
1 GiB (native-owned-businesses), 2 GiB (subcontracting), chosen so the replay
could actually run rather than to flatter the retention figure.

## 10. Three defects found in the replay machinery itself

The clean room tests the manifest as hard as it tests the pipeline. It failed
three times, and all three were `516`'s fault.

### G1 — retention discarded mtimes that the pipeline reads as data

Directory inputs were retained as a zip with every entry stamped
`(1980,1,1)` "for determinism" — determinism the design did not need, because a
directory blob is NAMED by its tree's merkle root, not by the archive's own
bytes. Separately, `ZipFile.extractall` **does not restore timestamps at all**:
measured on this interpreter, an entry stamped 2017 extracts with the current
wall clock.

Neither mattered until `77` was fixed to read `fetched_date` off the cached
artifact's mtime. From that moment the retention layer was handing the clean
room a 6,700-file corpus whose every document claimed to have been fetched on
the day of the replay, and `nagpra_notices.csv` could not have reproduced for a
reason belonging entirely to us. **The fix to B4 turned a filesystem timestamp
into data, and the retention layer was throwing it away.**

Fixed: directory blobs are now `zip_of_tree_v2_mtime_preserved`; a v1 blob is
rewritten in place on the next capture (the merkle name does not change, so
every existing manifest keeps pointing at the right tree and gains the
timestamps it should always have had); and `_extract_tree` re-stamps every
restored file from its zip entry. Two limits are recorded in the manifest
rather than discovered later: zip timestamps have 2-second granularity, and zip
stores local time with no zone, so restoring in a different timezone shifts
every mtime by the offset.

### G2 — the clean room was seeded with the release's own answers

`discover_inputs` computed a `role` for every input and `replay` ignored it.
Three consequences, each found by a crash:

- `data/clean/subawards.csv` is `20_build_subcontracts.py`'s own output. It was
  restored read-only on top of the rebuild target: `PermissionError`. Worse
  than the error is the version that does not error — the phase-2 enrichers
  would then have run against the **released** table, and the compare would
  have graded the release against itself.
- `data/clean/nd_severance_allocation.csv` is one of natural-resources' nine
  shipped tables and is also read by a sibling script, so discovery called it
  an input. Same failure. Roles now include `output_of_this_collection`,
  computed from the collection's own table list, which discovery cannot know
  and `build_collection` can.
- `review/resource_ledger_unresolved.csv` is a report `83` writes. Restored
  read-only: `PermissionError` on a file nobody was reading. Inputs now carry
  `written_in_scope`, and anything the run declares a write of is restored
  **writable** — the read-only guarantee still holds for everything else.

A basename-matching bug rode along with this. `declared_io` reports basenames,
and `_SOURCE_MANIFEST.csv` exists in 40-odd raw directories. One script in
scope writes one of them, so the basename match condemned
`data/raw/external/tribal_tax/_SOURCE_MANIFEST.csv` — a pure input to `108`,
and the file that tells it which six state corpora to parse — as this
collection's own intermediate. It was withheld, `108` logged
"MI: source unusable, skipped" nine times, and `tribal_tax_bases.csv` replayed
24 rows. The intermediate rule now applies only under `data/clean` and
`data/spine`, where Cedar's table names are unique and the basename can be
trusted.

### G3 — the clean room was not sealed, and it wrote to the live tree

**This one caused real damage. It is recorded in full.**

Adaptation A1 rewrote the hardcoded project root only in the scripts the
manifest's closure names. The other ~280 scripts carrying
`Path(r"C:\Users\esm247\Desktop\Cedar Press")` sat inside the clean room still
pointing at the **live tree**. The manifest's closure is a description of what
the release ran; it was being used as a boundary, and those are not the same
thing.

It fired. Testing whether native-owned-businesses' AMBIGUOUS script would
unblock its plan (§9d), `241_promote_individual_native_firms_in_place.py` was
run inside that clean room. It was not in scope, so it had not been rewritten,
so it read and wrote the live tree. At `2026-08-29 06:28:09 -0400` four live
files were written:

```
data/clean/individual_native_firm_register.csv    CHANGED - lost the cedar_uid
                                                    column 503 had stamped in;
                                                    built_date 08-26 -> 08-29
                                                    on all 45 rows
data/clean/individual_native_exclusion_pairs.csv  CHANGED - flagged_date
                                                    re-dated on all 5 rows; two
                                                    frozenset-repr columns
                                                    re-ordered
data/spine/cedar_entity_spine.csv                 rewritten, BYTE-IDENTICAL
data/clean/cedar_identifier_ledger_final.csv      rewritten, BYTE-IDENTICAL
```

**Remediation, verified.** The two changed files were restored byte-for-byte
from `241`'s own `.bak_2026-08-29_pre_241_…` backups, with their original
mtimes; sha256 and row counts re-checked afterwards, and `cedar_uid` is back in
the register (45 rows, 90,897 B, sha `c34c882a457cb361…`). The two
byte-identical files had only their mtimes moved; those were restored from the
same backups after confirming content equality first. One file is **not**
restored and is named here rather than omitted:
`review/individual_native_canonical_name_privacy_2026-08-29.csv`, a dated
review artefact that the 03:22 run of the same script had already created that
morning and for which no backup exists. Nothing else in the tree was touched:
no live file carries an mtime after 06:28:09 that belongs to workstream G.

**Fixed.** A1 now rewrites **every** `code/*.py` in the clean room — 281 files
for these releases — records per file whether it was in the release's scope,
then re-scans the room and prints a warning naming any file that still contains
the live root. Re-tested by firing: after the fix, the same 241 run inside the
same clean room aborts on its own missing inputs and writes nothing outside the
room, confirmed by `find` over the live tree.

One incidental determinism defect surfaced from the diff and deserves a line:
`individual_native_exclusion_pairs.csv` stores `repr(frozenset(...))` in
`firm_name_core` and `excluded_entity_name_core`. Set iteration order over
strings is not stable across processes, so those columns differ between two
runs that computed the same set. It is not a run-stamp column, so `compare`
will not set it aside, and it is not workstream G's file to fix.

## 11. Input discovery: a third spelling and a fourth channel

Part I named three discovery channels. Two more were needed, both found by a
clean room refusing to run.

**Channel 2b — path EXPRESSIONS, not just path constants.**
`20_build_subcontracts.py` spells its inputs as
`os.path.join(CEDAR, "data", "raw", "esm_hci", "ESM")` and then as
`os.path.join(ESM, "raw", "subcontract-…csv")` inside a module-level list of
tuples, bound to no name at all. Channel 2 resolved neither spelling, the five
files were never retained, and the replay died at `IndexError: list index out
of range` under five `MISSING INPUT (skipped)` warnings. 516 now resolves
`os.path.join` and `/` chains **anywhere** in a module against the module-level
name environment, built in file order with the same resolver.

That also settles an ambiguity nothing else could. Five of those files exist
**twice** under `data/` — once in `data/raw/esm_hci/ESM`, once in
`data/raw/external/subcontracts`. `resolve_filename` correctly refused to guess
between two hits and returned `None`, which is exactly how they became
`undiscovered`. A filename is ambiguous; a path is not.

**Channel 4 — manifest-driven expansion.** There is a class of input no static
channel can reach: one enumerated at RUNTIME from a data file. `108` reads
`_SOURCE_MANIFEST.csv` and opens whatever its `file` column names. These reads
never even reached `undiscovered_inputs`, because the io scanner sees an
`open()` on a variable rather than an unresolvable name — they were invisible
in both directions. 516 now reads a discovered `_SOURCE_MANIFEST*.csv` and
expands the files it names, relative to the manifest's own directory. For
natural-resources that is **+15 inputs**, and `tribal_tax_bases.csv` moved from
24 replayed rows to 96.

A **namespace rule** keeps this from over-collecting: a discovered directory
with a discovered file or subdirectory beneath it is a namespace, not a corpus,
and is dropped in favour of its named children. Without it the five ESM files
would have cost a 5.5 GB tree, and `data/raw/federal_register` would have been
retained whole to obtain the 18 MB corpus underneath it. This is
`CONTAINER_DIRS`' hand-maintained distinction, computed instead of listed.

**Measured effect, release-wide** (`516 survey`, no hashing, no CSV parsing):

```
                              part I      now
undiscovered reads              236        203
collections affected             11         11
inputs named                    513        582

input footprint, MB       part I      now     what changed
  gaming                  13,954   8,046     container dirs replaced by named children
  legislation             16,592   2,138
  _entity_layer           16,708   2,938
  nonprofits              17,261   2,021
  lobbying                16,438   2,270
  deals                   14,379   1,113
  subcontracting              65   1,882     os.path.join inputs became visible
  natural-resources          430     311
```

The large collections' footprint collapse is not a saving; it is a correction —
those figures were inflated by container directories counted as inputs, the
same error `CONTAINER_DIRS` was written to prevent, one level down.
Subcontracting moves the other way, and that direction is the one that matters:
it was never a 65 MB collection, and a manifest that said so would have
certified a release while its five substantive raw inputs went unretained.

Two new 516 commands, both cheap:

```
py -3 code/516_release_manifest.py survey    # per-collection replay footprint
py -3 code/516_release_manifest.py stamps    # the D4 breakdown, §12
```

## 12. D4 / B4, broken down so each fix is a lookup

Part I reported "284 run-stamp columns" and stopped there. A count is a size,
not a work plan: fixing one still meant finding which table carried it and
which of 385 scripts wrote it. `516 stamps` now produces
`docs/releases/_analysis/run_stamp_breakdown.json` — collection, table, column,
the constant value it holds, and the script(s) that write that column into that
table.

**283 columns across 255 tables and 12 of 13 collections.** The drop from 284
is exactly one: `nagpra_notices.fetched_date`, fixed and proven by bytes in
§9a. **nagpra is now the only collection at zero.**

```
collection                tables w/ stamps   columns      by COLUMN NAME
funding                          9              9      built_date         112
federal-register                16             24      fetched_date        53
legislation                     11             12      retrieved_date      13
deals                           15             24      retrieved_at        12
nagpra                           0              0      entity_link_date    11
lobbying                        29             38      entity_keyed_date   10
contractors                      8              9      Data_As_Of           8
subcontracting                   1              1      Date_Added           8
native-owned-businesses          6             10      build_date           5
natural-resources                7             10      ruled_date           5
nonprofits                      12             19      first_seen           3
gaming                          46             93      last_seen            3
_entity_layer                   30             34
```

**How much of this is now a lookup rather than an investigation:**

```
206 of 283   a script that DECLARES A WRITE of the table also contains the
             column name                      -> open that file, find that line
 15 of 283   a declared writer exists but the column name is not in it; the
             column is inherited from an upstream frame
 46 of 283   no declared writer contains it; attributed to scripts that name
             both the table and the column
 16 of 283   UNATTRIBUTED
205 of 283   the attributed writer is IN that collection's build plan
```

The largest single concentration is `gaming` (93 columns over 46 tables), then
`lobbying` (38). By name, `built_date` (112) and `fetched_date` (53) are 58% of
the debt and both take the same one-line fix, already demonstrated:
**`code/77_build_nagpra_dataset.py::cache_fetched_date` — derive the date from
the cached artifact, and leave it BLANK when the artifact cannot say.**
Blank-when-unknown is the point; a date invented at build time to fill a column
is a lie that reproduces.

**One caveat the file states about itself.** A column whose every non-blank
value is a single ISO date is a run-stamp *candidate*. A table that legitimately
covers one day is a false positive of the same test — two columns hold
`1998-05-20`, which is nobody's build date. The constant value is printed
beside every column so a reader can tell the two apart, and nothing is
auto-fixed.

**No pipeline script was edited by workstream G. The breakdown is the
deliverable.**

## 13. D9 — closed for these captures, and enforced rather than hoped

Part I's D9 was "a release capture is only valid on a frozen tree, and nothing
enforces the freeze". 516 now enforces it.

`build --require-quiescent` re-checks, at the end of every capture:

```
inputs    sha256 + (mtime, size)    content, and the FACT of a write
outputs   (mtime, size)             the released hashes just taken are void if
                                    the table moved after they were taken
```

Content-only re-hashing under-detected. A rewrite that lands the same bytes
still means another process held the file open and wrote it while we were
reading the rest of the collection, and an `--apply` run that ends in an
identical write is exactly the shape of the pipelines running beside this pass.
Outputs are checked on stat rather than content deliberately — rehashing a
1.0 GB table to learn what a stat call already said doubles the cost of every
capture — and that asymmetry is recorded in the manifest instead of being left
for a reader to discover.

On failure the capture is **refused**: it is not filed under
`docs/releases/<id>/`, the evidence is written to `docs/releases/_rejected/` so
the refusal itself is auditable, and the command exits non-zero so a caller
redoes it rather than shipping it.

**All four captures in this pass were taken with `--require-quiescent`, and all
four reported `quiescent: True`** — 76 file inputs and 25 outputs re-checked,
zero movement, while workstreams E and F were writing other parts of the tree.
D9 is **CLOSED for these four releases** and remains open as a project-wide
guarantee, because nothing yet stops a capture taken *without* the flag. The
one-line request is in §15.

## 14. Debt ledger — deltas, measured

| id | part I | now | movement |
|---|---|---|---|
| **D1** `code_not_relocatable` | 280 of 385 scripts | **unchanged, 280** | not this pass's file; the solo de-hardcode pass is next. A1 now rewrites all 281 present in the clean room (§10 G3) |
| **D2** `output_stale_vs_input` | 2 of 4 nagpra tables | **4 of 4 captured collections flag it**; nagpra still 2 of 4, proven twice | UNCHANGED in kind, wider in measure. Every collection captured on a *frozen* tree still has an output older than a recorded input, so 260/260 was not purely a quiescence artefact |
| **D3** `undeclared_enrichers` | 13/13 collections | **4 of 4 captured collections**, unchanged | still `503_identity.py`'s runtime dispatch. nagpra's bridge reproduces only because 503's stamp is currently ABSENT from the release — the debt is masked, not paid |
| **D4** `nondeterministic_output_columns` | 284 across 13/13 | **283 across 12/13**, fully broken down per table, column and writer | −1, proven by bytes; nagpra at 0. §12 |
| **D5** `collections_never_replayed` | 12 of 13 (1 replayed, 4 of 260 tables) | **9 of 13** (4 replayed, **25 tables compared, 4 byte-identical**) | **IMPROVED**. First byte-identical replays in the project |
| **D6** `release_inputs_referenced_only` | 296 MB for 1 collection | **3,032 MB store; 76 of 76 inputs retained across 4 collections, 0 referenced-only** at the thresholds used | measured. At the DEFAULT 512 MiB threshold, `prime_contracts.csv` (816 MB) and one 1.2 GB subaward corpus are referenced-only — 2 of 76. Thresholds are per release and recorded per release |
| **D7** `plan_scripts_missing` | 3 collections, by inspection | **unchanged, 3**; one now confirmed BY EXECUTION (`update_index.py`, §9c) | evidence upgraded from inspection to a traceback |
| **D8** `undiscovered_inputs` | 236 across 11 of 13 | **203 across 11 of 13**; subcontracting 6→2, natural-resources 4→3, nagpra 0; inputs named 513→582 | **IMPROVED** by channels 2b and 4 (§11). Subcontracting's residue is 2 runtime lock/state files that do not exist on disk |
| **D9** `release_captures_non_quiescent` | 2 inputs rewritten under the 13-collection sweep | **0 across 4 captures**, enforced by `--require-quiescent`, refusal path tested | **CLOSED for these captures**; open project-wide until the flag is the default |
| **D10** *(new)* `build_plan_calls_a_live_api` | — | **1 known**: `121_pull_subawards_api.py`, in subcontracting's plan. 4 of its 5 fiscal years failed in the clean room because the source's tokens expired | a release whose plan fetches at build time has the internet as an input. Retention cannot hold it and no threshold change helps |
| **D11** *(new)* `tables_no_planned_script_writes` | — | **7 of 9 native-owned-businesses tables have no phase-1 writer at all (0 planned rebuilders); 3 of 9 natural-resources tables have no writer in the plan** | distinct from D7: the script exists, the PLAN never calls it, usually because `build.py` classified it AMBIGUOUS |

## 15. Changes needed in files workstream G does not own

Carried forward from part I §7 and still open: register D1–D6 in
`62_no_regression_check.py`; give `503_identity.py` a machine-readable run
record; mention post-chain step 8 in `docs/SHIPPING_RUNBOOK.md`.

New this pass:

1. **`code/62_no_regression_check.py` (integrator)** — add
   `release_captures_non_quiescent` MUST_BE_ZERO and
   `nondeterministic_output_columns` MUST_NOT_RISE **at a floor of 283**, so
   the next `built_date` that lands fails the gate the day it lands.
   `516 stamps` prints the number.
2. **`code/build.py` (integrator)** — `ship --execute` should pass
   `--require-quiescent` to step 8. The flag exists, is tested, and refuses
   correctly; nothing currently makes it the default, and that gap is the whole
   of what D9 still is.
3. **`code/121_pull_subawards_api.py`** — it is planned as an enricher and it
   fetches. Either split the fetch into a stage the plan does not run (as `77`
   does) or declare the collection unreplayable by construction. D10.
4. **`cedar_pipeline.KNOWN_ORDERINGS`** — declaring an ordering for
   `241_promote_individual_native_firms_in_place.py` and
   `135_build_resource_assets.py` would place two AMBIGUOUS scripts that are
   each the only writer of tables their collection ships, and would unblock two
   collections' plans. D11.
5. **`code/241_promote_individual_native_firms_in_place.py`** — writes
   `repr(frozenset(...))` into two CSV columns; set iteration order is not
   stable across processes (§10 G3).

## 16. Verdict, restated

**Commercial-release condition "a release successfully replayed from retained
immutable inputs": still PARTIALLY MET — but the sentence part I could not
write can now be written.**

- **4 tables are byte-identical on replay** — 6,772 + 51,521 + 220 + 304 rows
  across 2 collections, sha256 equal on both sides, produced from inputs
  restored out of the blob store with nothing read from the live tree.
- 4 of 13 collections have been replayed and graded; 25 tables compared.
- All 4 captures were taken on a tree proven quiescent, by the tool, at capture
  time — the first captures in this project of which that is true.
- 76 of 76 inputs retained and re-verified; the store is 3,032 MB and `verify`
  exits 0 over every blob of every release.

And, in the same breath:

- **21 of 25 replayed tables did not reproduce.** Ten of those were not
  produced at all, because two collections' plans do not name a writer for
  every table they ship.
- One collection's plan **calls a live API**, which no retention policy can make
  replayable.
- 9 of 13 collections remain unreplayed.
- The replay machinery itself had three defects (§10), one of which wrote to the
  live tree before it was caught. It was caught, measured and reversed, and it
  is written down here because a log that records only the pipeline's faults is
  not evidence.
