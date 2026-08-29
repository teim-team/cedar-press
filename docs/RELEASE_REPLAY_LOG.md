# Release replay log

*Workstream C, 2026-08-29. External review finding **F13**, ADR-004. This
document is the evidence for one claim and the refutation of a larger one.*

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
