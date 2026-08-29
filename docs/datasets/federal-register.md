# `federal-register` — the update procedure

*Closure pass, 2026-08-29. Status on `docs/DATASET_READINESS.md`: **READY**, 22
customer tables. This document is written to be executed by a session with **no
knowledge of how the dataset got here**. Every command below is complete as
written and is run from the repository root (`Desktop/Cedar Press`) with
`py -3`. Where a step is dangerous the danger is stated at the step, not in a
preamble somewhere else.*

The dataset's contract — grain, primary key, join cardinality per table — is
`docs/schema/dataset_contracts.json`, collection `federal-register`. The prose
overview of what the tables mean is `docs/datasets/09_federal_actions.md`,
`docs/CONSULTATION_BUILD_LOG.md` and `docs/CONTENT_ANALYSIS.md`. This file is
only about **how to update it and how to prove the update is sound**.

---

## 0. The one-screen version

```bash
# ---- FETCH (routine refresh; appends, never rebuilds) --------------------
py -3 code/342_pull_federal_register_incremental.py

# ---- NORMALISE / DERIVE (only the stages whose inputs actually moved) ----
py -3 code/78_content_analysis.py            # READ STEP 2 FIRST - cross-dataset
py -3 code/70_key_unjoined_datasets.py
py -3 code/96_build_consultation_events.py all
py -3 code/130_build_section_106_consultation.py all      # not in build.py's plan
py -3 code/134_build_nepa_eplanning.py all
py -3 code/154_build_fr_ex_parte_notices.py build

# ---- RESOLVE IDENTITIES --------------------------------------------------
py -3 code/69_enrich_spine_from_federal_register.py   # only on a new FR roster
py -3 code/514_source_records.py all --apply
py -3 code/510_assertions.py all --apply
py -3 code/503_identity.py stamp --apply

# ---- VALIDATE ------------------------------------------------------------
py -3 code/519_closure_federal_register.py conserve
py -3 code/519_closure_federal_register.py verify
py -3 code/519_closure_federal_register.py fixtures
py -3 code/514_source_records.py verify
py -3 code/510_assertions.py verify
py -3 code/512_build_dataset_contracts.py verify
py -3 code/518_dataset_readiness.py
py -3 code/62_no_regression_check.py

# ---- SHIP (integrator only) ---------------------------------------------
py -3 code/build.py ship --execute
```

**`py -3 code/build.py run federal-register --execute` is NOT the update
command.** Read step 7 before you use it. Its plan is incomplete in two places
and destructive in one, and all three are named below.

---

## 1. FETCH

### The routine refresh

```bash
py -3 code/342_pull_federal_register_incremental.py
```

`342_pull_federal_register_incremental.py` carries the corpus forward from
`max(publication_date)` in `data/clean/federal_actions_raw.csv` to today. It
reuses `10_pull_federal_register.py`'s own `harvest_shard`,
`11_classify_federal_actions.py`'s own `classify()` and
`22_apply_temporal_floor.py`'s own `year_of()`, and **appends** to both
`federal_actions_raw.csv` and `federal_actions.csv`. Nothing already on disk is
refetched or rewritten.

It merges only if **every** net completed and every retrieved count equals the
count the API itself reported; otherwise the fetched shards stay on disk as
cache, the CSVs are untouched, and the run records `INCOMPLETE`. Re-run it; it
resumes for free. That contract exists because the next run derives its start
date from the file, so a silently partial window would make the skipped days
permanently unreachable.

Cache lands in `data/raw/federal_register/*.jsonl.gz` in `10`'s shape.
`data/raw/federal_register/_shard_manifest.csv` is written by `10` only and is
**stale by design after an incremental run** — it was last written 2026-08-05
and does not list the eleven shards `342` added on 2026-08-26. **The directory
is the population, not the manifest.** `519`'s conservation ledger reads the
directory for exactly this reason.

### The full re-harvest — rare, and it costs two extra steps

Only when the net definitions or the 1994 floor change:

```bash
py -3 code/10_pull_federal_register.py        # hours; 14 nets x 33 years
py -3 code/11_classify_federal_actions.py     # FULL REBUILD of federal_actions.csv
py -3 code/22_apply_temporal_floor.py         # MANDATORY - see below
```

`11` writes 31 of `federal_actions.csv`'s 33 columns. The other two —
`pre_2000_flag` and `floor_basis_field` — are written **in place** by
`22_apply_temporal_floor.py`, and the shipped view filters on `pre_2000_flag`.
Running `11` without `22` after it ships a table whose default filter column
does not exist. The ordering is declared in
`cedar_pipeline.KNOWN_ORDERINGS` (`11 → 22`, file `federal_actions.csv`), so
`py -3 code/build.py plan federal-register` now prints
`federal_actions.csv -> re-run 22_apply_temporal_floor.py`.

---

## 2. NORMALISE / DERIVE

Run only the stages whose inputs moved. Each is independent of the others
except where stated.

### `78_content_analysis.py` — READ THIS BEFORE RUNNING IT

`78` produces six of this collection's customer tables
(`fr_content_classification`, `fr_theme_year`, `fr_relevance_tier_year`,
`fr_consultation_notices`, `fr_consultation_referenced`, `fr_consultation_year`,
`fr_consultation_by_agency`, `fr_abstract_availability_year`) **and four
`lobbying` tables and two `nagpra` tables**, from one `main()`. It has a
`--nagpra-only` flag which holds the non-NAGPRA writes back. It has no
`--fr-only` flag.

So a full `78` run rewrites `lobbying_issue_families_filing.csv`,
`lobbying_issue_family_year.csv`, `lobbying_disclosure_verbosity_year.csv`,
`lobbying_target_entities.csv`, `agency_attention_vs_advocacy*.csv` and
`content_analysis_accuracy.csv` from whatever the lobbying tables hold that
day. Two orderings are declared for this in `cedar_pipeline.KNOWN_ORDERINGS`:
after a full `78` run you owe
`353_propagate_lobbying_corrections_to_consumers.py` and then
`503_identity.py stamp --apply`, or the lobbying corrections and the
`cedar_uid` stamp are both reverted.

**This is why `federal-register` currently carries a 320-row `stale:` bucket.**
`78` last ran for this collection on 2026-08-06; `342` added 320 documents on
2026-08-26; `lobbying_issue_families_filing.csv` was rewritten by another
workstream on 2026-08-28. Re-running `78` closes the 320-row gap and reverts
that workstream's table in the same command. The gap is therefore **named and
counted** in the conservation ledger rather than closed unilaterally:

```
data/clean/fr_content_classification.csv   156,772 rows read
      156,452  emitted
          320  stale:published_after_the_last_78_content_analysis_run_so_no_
               classification_row_exists_for_it_yet
```

`519 conserve` **refuses** to call that bucket stale unless every one of the
320 documents postdates the last publication date the classifier covers, so
the label cannot quietly absorb a real drop.

To close it: coordinate with whoever owns `lobbying`, then

```bash
py -3 code/78_content_analysis.py
py -3 code/353_propagate_lobbying_corrections_to_consumers.py
py -3 code/503_identity.py stamp --apply
py -3 code/519_closure_federal_register.py conserve   # the stale bucket goes to 0
```

### The other builders

| command | writes | notes |
|---|---|---|
| `py -3 code/70_key_unjoined_datasets.py` | `federal_actions_entity_bridge.csv` | **Invisible to `build.py plan`** — its write helper is `wr(`, which 293's io scan does not recognise, so the table has no rebuilder in the io map. Run it by hand after `11`/`342`. |
| `py -3 code/96_build_consultation_events.py all` | `consultation_events.csv`, `consultation_agency_coverage.csv` | stages `fetch` → `agencies` → `build`. Reads `fr_consultation_notices.csv` + `fr_consultation_referenced.csv`; run it **after** `78`. Network. |
| `py -3 code/130_build_section_106_consultation.py all` | `section_106_consultation_events.csv`, `section_106_project_parties.csv`, `section_106_source_coverage.csv` | stages `enumerate` → `fetch` → `build`. **Not in `build.py`'s plan at all** — it rebuilds one table and enriches two, which `build.py` reports as AMBIGUOUS and excludes. Its hand position is: after `11`/`342`, before `503`. Network. |
| `py -3 code/134_build_nepa_eplanning.py all` | `nepa_eplanning_projects.csv`, `nepa_project_documents.csv`, `nepa_administrative_record_parties.csv`, `nepa_source_coverage.csv` | stages `register` → `details` → `build`. Independent of the FR corpus; sourced from BLM ePlanning. Network, host-locked. |
| `py -3 code/154_build_fr_ex_parte_notices.py build` | `fr_ex_parte_notices.csv`, `fr_ex_parte_parties.csv`, `fr_ex_parte_party_entity_links.csv` | full chain is `probe` → `index` → `probe2` → `candidates` → `fetch` → `build`; only `build` is offline. Network for the rest. |

---

## 3. RESOLVE IDENTITIES

This dataset is the only one in Cedar whose identity runs through the
**source-record layer** (`docs/SOURCE_RECORD_LAYER.md`). The design point is
that *what a source says* and *who Cedar thinks it means* are two tables, so a
bad match can be refuted without refuting the fact.

### `69_enrich_spine_from_federal_register.py` — only on a new roster

Run it only when a new "Indian Entities Recognized by and Eligible To Receive
Services" notice has been saved to
`data/raw/external/fr_recognized/<doc>_raw.txt`. It rebuilds
`data/clean/fr_recognized_entities.csv` from that text and adds aliases to the
spine in place.

**Measured on 2026-08-29, against the current roster on disk, without writing
anything:** re-running `69` today changes **one cell** —
`Native Entities Within the State of Alaska Recognized by and Eligible To
Receive Services From the United States Bureau of Indian Affairs` moves from
`kind = entity` to `kind = section_heading`, which is correct (it is the
Alaska list's TITLE, and the heading classifier was added after the file on
disk was written). 575 rows in, 575 rows out, 0 added, 0 lost. On the spine it
is a **complete no-op**: 1,536 rows compared, 0 changed, 0 aliases added, the
44-column header identical. So the "69 rewrites the spine wholesale and 16
orderings depend on it" fear is, on today's data, unfounded — and it was
measured rather than assumed.

**But it does not stand alone.** `514` content-addresses a source record as
`SR-sha1(dataset|locator)` where the locator embeds `kind`, so that one changed
cell re-mints one node id and one link id. Running `69` therefore obliges the
next two commands, in this order, or `514 verify` fails with SR10 (a source row
that never became a node):

```bash
py -3 code/69_enrich_spine_from_federal_register.py
py -3 code/514_source_records.py all --apply
py -3 code/510_assertions.py all --apply
```

The change is an improvement: that record currently asserts
`record_says_is_federally_recognized = yes` about a section heading, and after
the rebuild it asserts nothing. It reaches no customer table either way — it is
already refused into
`rejected:link_status_unresolved_no_eligible_cedar_entity_for_this_record`.

### `514` and `510`

```bash
py -3 code/514_source_records.py all --apply     # records -> links
py -3 code/514_source_records.py verify          # 10 invariants
py -3 code/514_source_records.py fixtures        # 13 fixtures
py -3 code/514_source_records.py determinism     # re-mints nothing
py -3 code/510_assertions.py all --apply         # harvest -> assertions -> facts
py -3 code/510_assertions.py verify
```

`510.harvest_fr_roster` emits **only** from links with
`link_role = identifies` and `link_status ∈ (verified, proposed)`. Invariant
I17 fails the build if a roster fact reaches an entity no accepted link names,
or if an accepted link produces no assertion.

**`510_assertions.py all --apply` REWRITES
`data/clean/cedar_harvest_conservation.csv` from its own ledgers**, which
deletes this dataset's 42 row-groups. The repair recomputes nothing:

```bash
py -3 code/519_closure_federal_register.py conserve --publish-only
```

Run it any time `62` reports `harvest_source_rows_read` falling, or `518` puts
`federal-register` back to BLOCKED on C5. `519 verify` names this command in
its own failure text.

### `503_identity.py stamp --apply`

Seven of this collection's tables carry `cedar_uid` — `consultation_events`,
`federal_actions_entity_bridge`, `fr_ex_parte_parties`,
`fr_ex_parte_party_entity_links`, `nepa_administrative_record_parties`,
`section_106_consultation_events`, `section_106_project_parties` — and `503`
discovers its tables at runtime, so no static scan attributes it. All seven
orderings are now declared in `cedar_pipeline.KNOWN_ORDERINGS`, so
`build.py plan federal-register` names `503_identity.py` instead of `unknown`.
**Any rebuild of one of those seven owes a `503 stamp` afterwards**, or the
table ships without the column a buyer joins on. The shipped release in
`dist/cedar_press.db` is currently in exactly that state (28 columns on
`consultation_events` where the live file has 29) because it predates the
stamp.

---

## 4. VALIDATE

```bash
py -3 code/519_closure_federal_register.py conserve   # rebuild the C5 ledgers
py -3 code/519_closure_federal_register.py verify     # exit 1 on any breach
py -3 code/519_closure_federal_register.py fixtures   # 8 fixtures, each proven
```

`519` is this dataset's closure gate and it re-derives everything from the live
files on every run:

* **C5 row conservation** — 22 ledgers, one per customer table, keyed by the
  OUTPUT table whose construction they account for (the convention
  `77_build_nagpra_dataset.py` established). `rows_in == sum(dispositions)`
  within every key; `other` / `unknown` / `misc` refused by name; a
  `DRIFT_` disposition if a recomputed aggregate stops matching the shipped
  table.
* **C1/C2 grain and keys** — every declared primary key re-tested for
  uniqueness and non-blankness on the **full** file. One blank key is allowed
  and only one: `fr_consultation_by_agency.csv`'s unattributed-department
  bucket, which the grain declaration names.
* **C3 duplicates** — whole-row hash over every one of the 22.
* **C4/C6 the identity path** — the class guard re-derived from the record's
  own `eligible_entity_classes` and the spine's `entity_class`, so a resolver
  change cannot bypass it; and no `fr_tribal_list` assertion may reach a
  customer through a `contested` / `denied` / `unresolved` link.

Then the Cedar-wide gates:

```bash
py -3 code/514_source_records.py verify
py -3 code/510_assertions.py verify
py -3 code/512_build_dataset_contracts.py verify
py -3 code/518_dataset_readiness.py
py -3 code/62_no_regression_check.py
```

### What `verify` looked like at closure, 2026-08-29

```
  22 shippable tables
  C5 conservation coverage   22/22
  C2 duplicate primary keys  0
  C3 literal duplicate rows  0
  C4 accepted identity links 567   class-guard breaches 0
  C6 FR assertions reaching a customer through a refused link: 0
  note: 1 fr_tribal_list assertion comes from the SPINE's fr_official_name
        column, not from a source record: ['CE-0010D-JE']
```

That one note is **not** this dataset's defect and is reported rather than
failed on. `510.harvest_spine` reads `cedar_entity_spine.csv`'s
`fr_official_name` column and stamps the roster's `source_id` on it, and
Bristol Bay Area Health Corporation carries an `fr_official_name` value that
appears **nowhere in the roster file**. `docs/SOURCE_RECORD_LAYER.md` records
it as belonging to the spine's owner: the source-record layer cannot refute a
value that is not one of its records.

---

## 5. Row conservation — what every ledger says

`review/federal_register_row_conservation.csv` is the durable copy;
`data/clean/cedar_harvest_conservation.csv` is the shared file `510`'s I13 and
`62`'s `harvest_rows_unaccounted` gate on. Each ledger declares how its
buckets were established:

* **RECOMPUTED** — the builder's own predicate was imported and re-run over the
  input on disk (`11.classify`, `78.fr_tier`, `78.fr_themes`,
  `78.CONSULT_TITLE` / `CONSULT_SUBJECT_ABS` / `CONSULT_BOILERPLATE`,
  `134.TRIBAL_RE`). Nothing is re-implemented, and the recomputation is
  reconciled cell-by-cell against the shipped table — a mismatch is a
  `DRIFT_` disposition and `verify` fails on it. At closure, **every
  reconciliation matched**: the recomputed theme series, tier series,
  consultation series, by-agency series and abstract series reproduce the
  shipped tables exactly.
* **MEASURED** — the disposition is established by key membership between the
  input and the output on disk; the REASON is the builder's documented rule
  (e.g. `70` writes a bridge row only where it resolved an entity).
* **SELF** — a coverage table is its own ledger. Every probe is a row by
  construction, including the probes that yielded nothing, which is the point
  of those tables.

Headline numbers at closure:

| output | rows read | emitted | the largest named refusal |
|---|---:|---:|---|
| `federal_actions_raw.csv` | 323,738 | 156,772 | 166,966 `duplicate:same_document_returned_by_another_net_or_another_date_shard` |
| `federal_actions.csv` | 156,772 | 156,772 | — |
| `fr_content_classification.csv` | 156,772 | 156,452 | 320 `stale:` (see step 2) |
| `fr_theme_year.csv` | 156,772 | 18,696 | 134,074 `no_native_term_in_the_title_or_abstract` |
| `fr_consultation_notices.csv` | 156,772 | 484 | 21,894 `neither_the_title_nor_the_abstract_carries_a_consultation_signal` |
| `federal_actions_entity_bridge.csv` | 156,772 | 4,991 | 151,781 `no_spine_entity_name_resolved` |
| `nepa_eplanning_projects.csv` | 66,889 | 312 | 66,577 `BLM_register_row_names_no_tribal_term` |
| `fr_ex_parte_parties.csv` | 7,820 | 71 | 7,749 `notice_text_carries_no_parseable_party_phrase` |
| `section_106_consultation_events.csv` | 1,422 | 1,240 | 182 `candidate_document_carries_no_Section_106_marker` |
| `consultation_events.csv` | 2,313 | 2,313 | — |

The 166,966 duplicates in the first row are not a defect: `10` runs fourteen
overlapping nets (one agency net and thirteen keyword nets) over the same
years, so a document about tribal land into trust is legitimately returned by
five of them. The dedup is on `document_number` and the ledger names it.

---

## 6. Semantic comparison against the current release

The current release is `dist/cedar_press.db` plus the per-table
`dist/*/**.notes.json` fingerprints, shipped 2026-08-26.

Compared table by table on 2026-08-29:

* **21 of 22 tables are in the release; row counts are identical on all 21.**
* **Value-level: zero rows differ.** Every row of every table small enough to
  compare whole (18 tables) is byte-equal on the release's own column set —
  `rows_only_in_release = 0`, `rows_only_live = 0` on every one.
* **7 tables have gained one column since the release: `cedar_uid`** —
  `consultation_events`, `federal_actions_entity_bridge`,
  `fr_ex_parte_parties`, `fr_ex_parte_party_entity_links`,
  `nepa_administrative_record_parties`, `section_106_consultation_events`,
  `section_106_project_parties`. Cause: `503_identity.py stamp` ran on
  2026-08-28, after the ship. **The advertised cross-dataset join key is in the
  live tables and NOT in the release.** The next ship closes it.
* **1 table is declared shippable and is absent from the release:**
  `fr_consultation_by_agency.csv`. Cause: its codebook block
  `09g_fr_consultation_by_agency` was registered on 2026-08-28, after the ship,
  and the codebook registry IS the shipping gate. The next ship closes it.

So the live dataset is a strict superset of the release: no value changed, one
column and one table were added. Reproduce the comparison with the queries in
`code/519_closure_federal_register.py` or directly against
`dist/cedar_press.db`.

---

## 7. The rebuild path, and where `build.py` is wrong about it

```bash
py -3 code/build.py plan federal-register --verbose
```

is worth running before anything else, because it prints the enricher backups
and now names the enricher owed for each. But **its plan is not the update
procedure**, in three specific ways:

1. **It runs `11` in phase 1**, which reverts `22_apply_temporal_floor.py`'s
   two columns (declared now, so the plan prints the warning — but the plan
   still does not run `22`). Prefer `342`.
2. **It omits `70_key_unjoined_datasets.py` entirely.** 293's io scan does not
   recognise `wr(` as a write, so `federal_actions_entity_bridge.csv` has no
   rebuilder in the map. Run `70` by hand.
3. **It excludes `130_build_section_106_consultation.py` as AMBIGUOUS** — it
   rebuilds `section_106_source_coverage.csv` and enriches two other tables, so
   `build.py` refuses to place it rather than guessing. Run `130 all` by hand,
   after `342`/`11`, before `503`.

Nothing in this collection is on `cedar_pipeline.NEVER_RUN`. The plan's phase 1
is `10`, `11`, `134`, `154`, `69`, `78`; phase 2 is `96`.

**Is a safe full rebuild possible?** Yes, with the three corrections above and
the `78` coordination in step 2. The order that is safe, stated once:

```
342  (or 10 → 11 → 22)
78              [cross-dataset — see step 2]
70
134 all
154 build
130 all
96 all
69              [only on a new roster]
514 all --apply
510 all --apply
503 stamp --apply
519 conserve
```

`69` is placed after the derivations rather than before because it is the only
step that writes the spine, and `503` must be the last thing that touches any
table carrying `cedar_uid`.

---

## 8. Known state, stated plainly

* **320 documents in `federal_actions.csv` have no `fr_content_classification`
  row.** Named, counted, and proven to be staleness. Closing it means running
  `78`, which reverts a `lobbying` table. Step 2 has the command.
* **`fr_ex_parte_party_entity_links.csv` links two datasets.** All nine of its
  rows come from `ferc_ex_parte_parties.csv`; `fr_ex_parte_parties.csv`
  resolves 0 of its 112 parties. A customer joining `fr_ex_parte_parties` to it
  gets **nothing**, and that is the data, not a broken key. The join key is
  `(source_dataset, source_row_id)`, never `source_row_id` alone. Now stated in
  the grain declaration.
* **`fr_ex_parte_parties.csv` and `section_106_project_parties.csv` carry
  `cedar_uid` at 0% .** The column exists; nothing resolved into it.
  `section_106_consultation_events.csv` is at 17.3%,
  `consultation_events.csv` at 91.2%.
* **`consultation_agency_coverage.csv` is UNDOCUMENTED**, not shippable, and
  outside the 22. `96` writes it; nothing declares its grain.
* **`_shard_manifest.csv` under-reports the FR cache by eleven shards.** See
  step 1. Anything that counts the corpus must read the directory.
* **The `natural_key_duplicate_rows` figures in `docs/schema/grain_evidence.json`
  are benign and now explained in the grain declarations**: 652 in
  `fr_consultation_referenced` (the FR reissues identically titled NAGPRA
  notices for different collections), 17 in
  `correspondence_foia_source_coverage` (one agency, several pages), 5 in
  `fr_consultation_year` (two quiet years with the same pair of counts). Zero
  literal duplicate rows anywhere in the 22.

---

## 9. Files this procedure owns

```
code/519_closure_federal_register.py             the closure gate (conserve/verify/fixtures)
code/512_build_dataset_contracts.py              the federal-register GRAIN_SWEEP entries
code/cedar_pipeline.py                           the federal-register KNOWN_ORDERINGS entries
docs/datasets/federal-register.md                this document
review/federal_register_row_conservation.csv     the durable C5 ledger
review/federal_register_closure_evidence.json    what verify last measured
```
