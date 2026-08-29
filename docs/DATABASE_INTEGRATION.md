# Database integration

*Written 2026-08-26 by the agent holding script numbers **284–292**. Every number
below was recomputed from the files by the scripts named beside it. Nothing here is
transcribed from another document — see §7 for why that rule earns its keep.*

The owner's ask was: *"Update the code so it's not buggy and can be integrated into
our database. The code isn't finalised, but we need to make this easy to update
moving forward."*

Two halves. **Not buggy enough to ingest** is §1–§4. **Easy to update moving
forward** is §5–§6. Nothing here rewrites the 280 build scripts; it adds three
shared modules and six numbered ones, and generates the artefacts a database needs.

---

## The one command

```
py -3 code/289_update_collection.py --go
```

Dry run by default — `--go` is required to execute. It runs preconditions, takes a
rollback snapshot, pre-flights the rebuild/enricher ordering, then runs
`cedar_codebook build → 62 → 87 → 102 → 110 → 25 → 27 → 284 → 285 → 287 → 288 → 62`,
stopping on any gate failure and printing what to read at each step.

Rollback: `py -3 code/289_update_collection.py --rollback <snapshot-dir>` — the path
is printed at the start of every run.

---

## 0. What was added

| | what | why it is a module and not a script |
|---|---|---|
| `code/cedar_keys.py` | digest primitives, the key registry, the hand-ruled overrides | one place a row identity is minted or judged |
| `code/cedar_pipeline.py` | declared I/O, rebuild-vs-enricher classification, the **hard** never-run guards | ordering has to be declared; a prefix has not implied order since 2026-08-07 |
| `code/cedar_schema.py` | streaming profile, codebook→schema, **the licence gate** | the gate must sit at the column definition |
| `code/284_audit_nondeterministic_keys.py` | the key audit, static + empirical | |
| `code/285_build_table_schemas.py` | typed schema per table, two SQL dialects | |
| `code/286_check_idempotence.py` | idempotence audit | |
| `code/287_build_dependency_manifest.py` | dependency manifest + survival check | |
| `code/288_build_collection_descriptors.py` | the product's Collection descriptors | |
| `code/289_update_collection.py` | the update path | |

Generated artefacts: `docs/schema/` (keys, per-table schemas, DDL, idempotence,
dependency manifest) and `dist/collections/` (descriptors).
**All of them are regenerated; none is edited by hand.**

---

## 1. Stable primary keys — the blocking defect

### What was already known

`ferc_filing_id`'s last segment is `abs(hash(filer_organization)) % 10000`
(`133_build_ferc_advocacy.py:1833`). Python randomises string hashing per process,
so **4 of 2,534 documents shared between the 2026-08-12 and 2026-08-26 builds kept
their id.**

### What the audit found beyond it

`284` reads every `code/*.py` for ids minted from outside the row, and every
`data/clean/*.csv` for what its key actually is. **62 findings, 21 BLOCKING.**

| class | severity | count | what it means |
|---|---|---:|---|
| `PROCESS_HASH` | BLOCKING | 4 | builtin `hash()` on a string |
| `OBJECT_ADDRESS` | BLOCKING | 15 | builtin `id()` — a memory address |
| `PROCESS_RANDOM` | BLOCKING | 1 | `uuid4()` |
| `RANK_DERIVED` | BLOCKING | 1 | assigned from a row's rank |
| `POSITIONAL` | WARN | 51 | assigned from a row's position |
| `BYPASSED_ID_SERVICE` | WARN | 4 | minted under a `cedar_ids.PREFIXES` prefix without `cedar_ids.allocate` |

**Three of these are new and were not recorded anywhere.**

1. **`earmarks.earmark_id`** — `99_build_earmarks_and_schedc.py:1887` builds the
   explanatory-statement branch as `f"EMK-E{fy}-{abs(hash(p.stem)) % 10**6}-{n:05d}"`.
   **The identical `hash()` defect as FERC, in a second table, previously unrecorded.**
   The `H` and `S` branches of the same function are positional instead — a lesser
   defect, but not a key either.
2. **15 uses of builtin `id()`** as a dictionary key across `84`, `85`, `99`, `103`
   and `171`. These are join keys inside a single process, not persisted, so they do
   not corrupt a database — but `id()` is reused after garbage collection, so two
   different objects can share one, and `103_build_california_gaming.py` uses
   `id(s)` across four separate dicts on rows it also mutates. Worth a look by that
   file's owner; not a schema blocker.
3. **`uuid.uuid4()` in `143_build_gaming_property_locations.py:372`** is a MIME
   multipart boundary, not an id. **Correct use.** Recorded so the next audit does
   not re-litigate it.

### The cross-reference — the finding neither half sees alone

A column can be **unique in every build and still be a corrupt key**. Static
analysis cannot see that; profiling cannot see it either. `284` intersects them:
for each flagged id, does any clean table's discovered primary key carry values with
that script's literal prefix?

**28 tables are keyed on a column that is unique today and not stable across
builds.** Each match is grounded in the values in the file, not in the column name —
five scripts mint a column called `observation_id`, and only one writes `EMP-OSHA-`.

The three fixtures the coordinator named are all re-found, independently, by the
data:

| table | column | minted by | measured cost |
|---|---|---|---|
| `ferc_docket_filings.csv` | `ferc_filing_id` | `133:1833` `PROCESS_HASH` | 4 of 2,534 ids survived a rebuild |
| `individual_native_firm_register.csv` | `verification_id` | `170:482` `RANK_DERIVED` | Cherokee Construction briefly carried Frontier Electronic Systems' ownership sentence |
| `gaming_employment_observations.csv` | `observation_id` | `100:1580` `POSITIONAL` | on a re-run 482 of 492 rows changed id; a merge would have appended 492 silent duplicates |

`284` runs that fixture set as a self-test on every run and prints **PASS/FAIL**. A
check that cannot re-find the bugs it was written for is a decoration — this repo
has measured what that costs, in the six sessions that learned to scroll past one
red line in `62`.

The third fixture is the one that justifies the whole cross-reference. `observation_id`
profiles as **3,246 distinct over 3,246 rows, 0 blank, full scan** — a textbook
primary key by every measurable property, and worthless.

### The declared key for every table

`docs/schema/keys.json`, from `284`. Natural where one exists, deterministic digest
where not, privacy surrogate where the natural key is a person.

| kind | tables | |
|---|---:|---|
| `natural` | 191 | a unique, non-null column prefix the source assigned |
| `deterministic_surrogate` | 27 | no short prefix is unique but the full row is; key on a blake2b digest |
| `privacy_surrogate` | 2 | natural key resolves to a natural person |
| `UNSTABLE_KEY_NEEDS_SURROGATE` | 28 | unique today, not stable across builds |
| `BLOCKED` | 21 | no unique non-null key found at all |
| `REFUSED_LICENSED` | 2 | vendor-licensed; never ingested |

**Never `hash()`.** `cedar_keys.stable_digest` is blake2b over NFKC-normalised,
case-folded, whitespace-collapsed parts joined on ASCII `0x1F` — a separator that
cannot occur in a CSV cell, so `("ab","c")` and `("a","bc")` cannot collide. It
refuses a row whose every key column is blank, because a digest of nothing is the
same digest for every such row: a duplicate key wearing a hash.

### The privacy surrogate

`cedar_domain` already reasons this through and `cedar_keys` **imports** it rather
than restating it: SAM's public entity search resolves a UEI to a legal name and a
street address, so for a firm whose legal name **is** a person's name, publishing the
UEI publishes the person by one hop. `cedar_domain.INDIVIDUAL_NATIVE_WITHHELD_FIELDS`
already withholds `awardee_uei` and `cage_code` for exactly that reason.

**A primary key must obey the same rule or it reintroduces what the field policy
removed.** `individual_native_firm_register.csv` and
`individual_native_firm_contracts.csv` therefore key on
`surrogate_entity_id` — a deterministic digest of the internal UEI — which is
already the field `cedar_domain.INDIVIDUAL_NATIVE_PUBLISHABLE_FIELDS` names.

**No salt, and the reason is stated rather than implied.** An unpersisted salt is
non-deterministic — the defect this whole layer exists to kill. A persisted salt is
recoverable by anyone holding the file. The protection is that **the UEI column never
ships**, not that the digest is secret. Saying it that way is the honest version.

### What must never be joined on

`cedar_keys.is_forbidden_join_column()` answers this, and `285` writes it into the
DDL as a comment beside the column:

```
-- DO NOT JOIN ON ferc_docket_filings.ferc_filing_id: abs(hash(filer_organization)) % 10000.
--   Join on docket_number, accession_number, filer_organization_as_recorded instead.
```

**Never join two artefacts on a rank when either derives from a file another agent
can write.** That is the `INV-nnnn` lesson and it is not fixed by making the rank
stable — it is fixed by not joining on it.

---

## 2. The typed schema, and the licence gate

`285` emits, per table: column name, canonical type, SQLite type, PostgreSQL type,
nullability, PK/FK, access tier, published flag, units, definition, and the licence
flag. Generated from the **codebook fragments** — which already carry label,
definition, `access_tier` and `published` for 2,759 variables — reconciled against a
streaming profile of the actual file.

**220 of 271 tables are ingest-ready (81.2%).** 28 blocked on an unstable key, 21 on
no key at all, 2 refused as licensed.

Where the codebook and the file disagree, **both are emitted and the disagreement is
named** — 606 columns. The **file wins** for the SQL type, because a database has to
load what is actually there. A schema that reported only the codebook would certify
the codebook.

### The licence gate is enforced at the column definition

`LICENSED_SOURCE_FILES` was declared a HARD GATE in `87_build_dataset_notes.py` and
referenced nowhere else in that file from 2026-08-06 to 2026-08-26. In that window
**404,236 populated DUNS values reached a shipping artefact.**

A gate at the export step is a gate that one un-gated export path walks around. So
the refusal now happens **where the column is defined**: a licensed column is never
given a definition, and nothing downstream can emit a column it was never given.

**10 columns refused, 416,261 populated values**, every one printed by name:

| table | column | populated |
|---|---|---:|
| `federal_funding_transactions.csv` | `recipient_duns` | 253,453 |
| `faads_transactions_all_agencies.csv` | `recipient_duns` | 152,899 |
| `funding_identifier_harvest.csv` | `recipient_duns` | 9,015 |
| `gaming_facilities.csv` | `casino_city_id` | 595 |
| `bie_uio_identifier_links.csv` | `duns_internal_only` | 144 |
| `faads_identifier_coverage_by_agency_year.csv` | `pct_with_duns`, `pct_with_duns_tribal_rows_only` | 77, 77 |
| `faads_transactions.csv` | `recipient_duns` | 1 |
| `subaward_identifier_harvest.csv`, `subaward_identifier_netnew.csv` | `duns` | 0, 0 |

Plus 2 whole-table refusals: `gaming_facility_metrics.csv` and
`gaming_property_capacity_history.csv`.

**Two of those refusals are over-refusals and are kept anyway.**
`pct_with_duns` is a *percentage*, not a DUNS value — `cedar_codebook.is_licensed_col`'s
regex matches the substring. Refusing a coverage statistic costs a
column; letting the regex be widened by whoever next finds it inconvenient is how
the gate died the first time. **A licence gate fails closed.** Recorded here so the
next reader knows it is a known cost, not an unnoticed bug.

### Registries are imported, never copied

`cedar_codebook.LICENSED_SOURCE_FILES`, `is_licensed_col`, `dataset_groups`,
`match_group`, `registered_tables`; `cedar_domain`'s publication policy;
`cedar_ids.PREFIXES`. A second copy of a licence list is a second thing to forget to
update — the failure that had "which datasets exist" answered three different ways
by `87`, `25` and `27`, all three disagreeing.

---

## 3. Idempotence

`286`. Two directions, because neither sees the other.

**Static.** `164_link_facility_hub_sources.py` was not idempotent: a second run
short-circuited on a column test and **silently rewrote its own log with 187
facilities reading "0 sources"**. The work was fine; the *record* of the work was
destroyed by the guard meant to protect it.

That shape is a **conjunction of two ordinary things** — a branch on whether a
column is already present, and a date-stamped log a same-day re-run overwrites.
Either alone is normal practice. Together they are the defect. **34 scripts carry
both.** `164` is the fixture and `286` re-finds it.

| signal | severity | scripts |
|---|---|---:|
| `SILENT_LOG_REWRITE` | BLOCKING | 34 |
| `POSITIONAL_IDS` | BLOCKING | 56 |
| `APPEND_MODE_TO_CLEAN` | BLOCKING | 2 |
| `COLUMN_PRESENCE_BRANCH` | WARN | 62 |
| `DATED_LOG_OVERWRITE` | WARN | 110 |
| `NO_PART_RENAME` | WARN | 34 |

`APPEND_MODE_TO_CLEAN` is `84_resource_recipient_side.py:1039,1043`, appending to
`resource_revenue.csv` and `resource_parties.csv`. A second run appends the same
rows again.

**Empirical — re-run residue.** If a non-idempotent build has already run twice, the
evidence is in the table: rows identical once the volatile columns (the id, the
build timestamp) are removed. That is exactly what 482-of-492 looks like from
outside. **60 tables carry residue, 319,802 rows.**

This deliberately does **not** re-run anything to test it. Re-running a build to
check whether it is safe to re-run is how this project loses work.

**Residue is a signal, not a verdict.** A table that legitimately holds one row per
(entity, year, programme) with no other distinguishing column will show residue and
be correct. What it rules *out* is a table with zero residue: that one cannot have
been double-appended.

---

## 4. Rebuild-vs-enricher ordering

`287`. The problem in one sentence: **nothing anywhere declared that one script
rebuilds a file another script enriches**, and the number prefix has not implied
order since 2026-08-07.

- `133 build` discarded 931 entity links and 9 columns written by `168` four minutes
  earlier, and **printed a LARGER row count that read as progress**.
- `09` has done the same to `50`.
- A **partial restore** left 102,615 filings drawn from 307 dockets described by a
  docket table listing 183. Neither file looked wrong on its own.

**37 contested files** — a full rebuild and an in-place enricher both write them.
That is the list of places the same collision can happen again. Five orderings are
declared explicitly in `cedar_pipeline.KNOWN_ORDERINGS`, each with what getting it
wrong cost.

The survival check compares every clean table against its newest
`.bak_<date>_pre_<script>` — the signal that an enricher touched it. **79 tables
carry one; 0 have lost columns**, agreeing with `62`'s
`files_with_columns_lost_vs_backup = 0`. When it is not 0, `287` names **which
enricher to re-run**, which is the part that turns the metric into an action.

Pre-flight, before any rebuild:

```
py -3 code/287_build_dependency_manifest.py --check prime_contracts.csv
```

Exit 0 = no enricher columns missing. Exit 1 = names the enricher to re-run after.

**The four never-run scripts are hard guards, not comments.**
`cedar_pipeline.guard()` raises `ForbiddenScript` for `01`, `09`, `41` and `88`.
`289` calls it before every step and all four are verified armed at the start of
each run. The override is a literal string a human has to type having read the
reason.

---

## 5. The update path

`289`. Documented in the header of this file. What it adds over
`docs/SHIPPING_RUNBOOK.md` is that it **runs**, and that its most important line —
*"NEVER run `41_build_codebooks.py`"* — is enforced rather than written.

Preconditions, all cheap, each one paid for by an incident:

- **Is anyone else mid-write?** Any `data/clean/*.csv` touched in the last 30
  minutes stops the run. On this machine, right now, five tables were. The run
  refused to start, which is correct.
- **Is a puller holding a host?** 266 lock files, 4 touched recently.
- **Is the codebook whole?** `cedar_codebook.py check` must print `SAFE`.
- **Are the never-run guards armed?** 4 of 4.

Rollback is a snapshot taken **before anything moves**, restored **by exact filename
from a manifest**. Never by glob — a glob restore once reverted seven files
belonging to two other agents and dropped the ledger from 20,577 rows to 20,559.

The gate runs **twice**: before, and again after. Step 1 says the state was clean
going in; only the second run says this chain did no harm. A chain that gates itself
only on entry can do damage and report success.

---

## 6. The product descriptor

`288` emits `dist/collections/<id>.json` — **59 collections** — against the real
contract in `server/cedar_press/collections.py`:

    id · name · short_name · origin · level · tracks · rows_label ·
    downloads · vintage · version · updated · sources · method

Everything Cedar-side lives under a separate `_cedar` key so the product contract is
not polluted with our provenance.

**The citation string is generated from the descriptor:**

    Lumecon, "{name}" ({version}, vintage {vintage}), Cedar Press collection,
    cedarpress.ai. Accessed {date}.

So a wrong `vintage` does not sit quietly in a config file — it propagates into every
citation anyone writes of this data. That is the whole reason these are computed.

### The vintage rule

FY2026 closes 2026-09-30. **FY2025 is the last complete fiscal year and every
calendar-2026 figure is YTD.** A descriptor may not name a period the data does not
cover. **42 of 59 collections are YTD and say so; 133 period labels were considered
and refused**, each refusal recorded in `_cedar.vintage_refusals` so the honesty is
auditable rather than asserted.

Three classes of column had to be excluded before the vintage was honest, and **all
three were found by running the generator and reading its output**:

1. **Build metadata.** `built_date` / `fetched_date` carry the date *this build ran*.
   The first run emitted `vintage = 2026-08-26 (YTD)` for 38 collections on that
   basis. Every one would have gone into a citation as the as-of date of the data.
2. **Future dates.** A gaming compact expiring in 2060 produced
   `vintage = 2060-12-31`. A forward-looking term is a fact the data *records*, never
   its as-of date. These now surface in `tracks` — *"1990 to 2026 (terms recorded out
   to 2060)"* — which is where they belong.
3. **Processing dates.** `prime_contracts.ruling_applied_date` is a single constant,
   `2026-08-26`, and it set prime contracting's vintage to today. Excluded by name
   **and** by a data property — a date column with fewer than 3 distinct values over
   100+ rows is a stamp, not a series — because name lists go stale and the data
   property catches the column nobody thought to name.

### Verified against recorded ground truth

- **`federal-funding` computes `2026-06-30 (YTD)`**, matching the recorded fact that
  assistance data stops 2026-06-30. Independent agreement, not a hardcoded value.
- **`prime-contracting` computes `FY2026 (YTD; FY2025 is the last complete fiscal
  year)`** — and the reason is a finding worth stating plainly:
  **`prime_contracts.csv` has no transaction-date column at all.** Its only date-ish
  columns are `fiscal_year`, `built_date` and `ruling_applied_date`. The recorded
  "prime data stops 2026-07-03" is **not in this table**, so this layer will not
  assert it. Anyone who needs a dated prime vintage has to add the column upstream.

### The three hand-typed values it contradicts

| declared | where | computed from the file |
|---|---|---|
| `rows_label = "1,248 rows"` | demo descriptor | **`935 deals`** |
| `vintage = "2026 Q2"` | demo descriptor | **`2026-08-20 (YTD)`** |
| `tracks = "2010 to current"` | demo descriptor | **`2000 to 2026`** |
| "3,300 rows" | `ASSUMPTIONS_AND_LIMITATIONS.md:1484` | **3,246** |

The last one is the sharpest test. 3,300 was the *planned* figure, written before the
merge was measured; 54 rows were later removed as misattributed. **A generator that
read the prose would emit the planned number.** This one reads the file.

`rows_label` counts the **canonical** table, not the sum of a collection's members.
Summing `01_deals` gives 1,725 — the promoted table plus its own parts, counted
twice. `cedar_domain.DEALS_TRUTH` already says *"the single truth for the deals
universe. Import this; do not glob."* `288` imports it.

### Two things `288` deliberately does not decide

- **The shelf** (`standard` / `pro` / `grove`) is a catalog decision on the app side,
  not a property of the file. Emitted as `null` with a note.
- **`origin` and `level`** must use the app's evidence-registry vocabulary
  (`SOURCE_ORIGIN`, `SOURCE_AVAILABILITY`). **This repo has no copy of that
  registry.** The values emitted are Cedar's best reading and are flagged in
  `_cedar.origin_level_note` as requiring validation before a PR. Inventing a
  vocabulary member is how two systems silently disagree.

### The absence vocabulary

Carried in every descriptor: `NOT_IN_SOURCE`, `BELOW_REPORTING_THRESHOLD`,
`OUT_OF_SCOPE_BY_CONSTRUCTION`, `SUPPRESSED`, `REPORTED_EMPTY`, `NOT_CHECKED`.

**Not merged with `cedar_domain.ABSENCE_VALUES`**, which is a different and narrower
set scoped to individual-Native ownership evidence (`NO_CLAIM_FOUND`,
`NO_SITE_FOUND`, `SITE_UNREACHABLE`, `NOT_CHECKED`, `UNDETERMINED`). `NOT_CHECKED` is
the only member of both. Collapsing them would let *"we did not sweep this firm's
website"* be read as *"the source reported nothing"* — exactly the distinction the
owner asked to preserve.

**Nothing is pushed from here.** The product repo takes a `claude/*` branch into a
PR, never a direct push to main.

---

## 7. Ingest-ready vs blocked

**Ready: 220 of 271.** Blocked: 49, in two kinds.

**28 `BLOCKED_UNSTABLE_KEY`** — the key is unique today and not stable across builds.
These *load*; they must not be foreign-key targets until the id is replaced with
`cedar_keys.surrogate_id()` over the source's own stated facts:

`admin_regional_observations` · `advocacy_passthrough` ·
`advocacy_passthrough_2026-08-07` · `anc_ceiling_roster` ·
`cedar_identifier_ledger_final` · `cedar_identifier_ledger_tiered` ·
`compact_events` · `compact_required_reports` · `compact_structured_terms` ·
`ferc_docket_parties` · `gaming_capacity_official` · `gaming_decision_events` ·
`gaming_employment_observations` · `gaming_manufacturer_facts` ·
`gaming_ordinance_ocr` · `gaming_ordinances` · `gaming_property_locations` ·
`individual_native_ownership_verification` ·
`individual_native_verification_candidates` · `nho_doi_notification_roster` ·
`nho_ownership_changes` · `nigc_declination_letters` · `nigc_revenue_bands` ·
`resource_revenue` · `section_106_consultation_events` ·
`section_106_project_parties` · `state_gaming_observations` ·
`wa_machine_allocations`

**21 `BLOCKED_NO_STABLE_KEY`** — no unique, non-null key exists at all. Three
sub-kinds, and they need different fixes:

- **Duplicate column names** — `entity_candidates_new.csv`,
  `entity_candidates_rejected.csv` carry `entity_category`, `parent_native_entity`,
  `parent_requirement` and `record_*` twice. **Every SQL dialect refuses the
  `CREATE TABLE`.** The producing script has to disambiguate them. (This also used
  to crash the profiler with a bare `KeyError`; it is now reported by name.)
- **Genuine duplicates** — `faads_transactions_all_agencies` has 53,709 rows
  duplicating on `(award_id_fain, source_url, recipient_name, obligated_usd)`;
  `subawards` 9,937; `np_schedule_i_grants` similar. A transaction table with exact
  duplicate rows either needs a sequence column from the source or has a real
  double-load.
- **Nothing ≥99% populated** — `congressional_correspondence_log` (0 rows),
  `deals_2026_ytd_additions`, `wa_machine_allocations`. Every candidate carries
  blanks, so nothing can be `NOT NULL`.

**Sampling is stated, never hidden.** Tables over 80 MB are scanned in a 300k-row
sample and every claim drawn from them carries `scan: sample:<n>`. A sample can prove
a key is *not* unique; it can never prove that it is. `288`'s date scan is **always
full**, because a sampled maximum date is a vintage that is too early, and a vintage
that is too early goes into a citation.

---

## 8. Named gate failure, and what this work did not touch

`62_no_regression_check.py` **FAILED before any of this work began**, on four
metrics, all caused by two tables written by other live agents minutes earlier —
`contractor_ranking.csv` (`269`, 19:00:09) and `individual_native_firm_register.csv`
(`241`, 18:59:02). Named with its owners in `AGENTS.md` per standing rule 3 before
proceeding, rather than recorded as "pre-existing, not mine".

**Resolved by those owners while this work ran.** The gate after: **exit 0, "no
regressions"**, with `ship_ratio_pct` at **92.547%** against the 65.202% baseline
this file opened on, `ship_dist_rows` at 7,444,230, and `lint_class7` — the key
check published from here — **falling 74 → 68**. Third time the naming rule has
been exercised end to end.

**This work writes nothing to `data/clean` and nothing to `dist/` except
`dist/collections/`.** It runs no build, fetches nothing, and re-reads every artefact
it writes rather than trusting the write — concurrency rule 4, because idempotence is
not enough when someone else is writing.

---

## 9. What to do next, in order

1. **Register the codebook fragments for `contractor_ranking` and
   `individual_native_firm_register`**, then re-run `the full 7-step ship chain (`py -3 code/build.py ship`; “87 → 25 → 27” is a 3-step shorthand that omits the codebook build, the gate, the coverage profile and the harmonised views)`. Both fragments
   already exist (`02h_`, `02i_`); they are not in the master. That clears the
   standing gate failure.
2. **Fix `earmark_id`.** It is the same `hash()` defect as FERC in a second table and
   nothing has keyed on it yet — which is the cheapest moment there will ever be.
   `cedar_keys.NON_DETERMINISTIC_COLUMNS` already carries the replacement key.
3. **Replace the 28 unstable ids** with `cedar_keys.surrogate_id()`. The highest
   value are the ones the product ships: `gaming_ordinances`,
   `section_106_consultation_events`, `resource_revenue`,
   `gaming_employment_observations`.
4. **Disambiguate the duplicate column names** in `entity_candidates_new` and
   `entity_candidates_rejected` — the only two tables that cannot be created at all.
5. **Add a transaction-date column to `prime_contracts.csv`**, or accept that the
   largest collection in the product cannot carry a dated vintage.
6. ~~Wire the key lint into `293` as class seven~~ — **done**, by its owner. See §10.
7. **Validate `origin` and `level`** against the app's `SOURCE_ORIGIN` /
   `SOURCE_AVAILABILITY` before opening the PR.

---

## 10. Class seven of the lint — done, by coordination rather than collision

`293_lint_bug_classes.py` covers six bug classes and wires into `62`. The
positional / non-deterministic-key check is **class seven**, and it is live:
`62` now reports `lint_class7` alongside the other six.

It was published from here as an importable function, never as a second runner —
a second lint is a second thing to run and a second thing to forget:

```python
import importlib
m = importlib.import_module("284_audit_nondeterministic_keys")
findings = m.lint_key_stability(severity_at_least="BLOCKING")  # list[dict]
ok, missed = m.lint_self_test()   # the three fixtures, re-found or not
```

Stable return shape: `script, line, klass, severity, target, mint_prefix, snippet,
why, affects_clean_tables`. `m.FIXTURES` holds the three measured instances.

**This file never edited `293`.** It was being written by its own agent at 19:11 on
2026-08-26, and editing another agent's in-flight script is precisely the collision
concurrency rule 5 is about. `293`'s own comment records the outcome — *"CONSUMED
from 284, never re-derived"* — and its owner wired it in without either of us
touching the other's file. That is the second time in one day the naming-and-handoff
convention has worked end to end.

---

## Regenerating any of this

```
py -3 code/284_audit_nondeterministic_keys.py     # keys + the lint      (~2 min)
py -3 code/285_build_table_schemas.py             # typed schema + DDL   (~20 s)
py -3 code/286_check_idempotence.py               # idempotence          (~2 min)
py -3 code/287_build_dependency_manifest.py       # ordering + survival  (~6 s)
py -3 code/288_build_collection_descriptors.py    # descriptors          (~45 s)
```

Add `--refresh` to `284` to re-profile every table from scratch; otherwise the
profile cache keys on `(size, mtime)` and a rebuilt table re-profiles automatically.
All five are read-only outside `docs/schema/` and `dist/collections/`.

---

## OPEN — the `origin` / `level` vocabulary is UPSTREAM, verified 2026-08-26

`284`-`289` correctly flagged that `origin` and `level` need validating against
the app's `SOURCE_ORIGIN` / `SOURCE_AVAILABILITY`. I cloned
`github.com/teim-team/cedar-press` and checked:

**`evidence.js` IS NOT IN THAT REPO.** Both `server/cedar_press/collections.py`
and `src/features/grove/collection.js` reference the vocabulary in a docstring
(*"origin and level use the evidence registry's vocabulary (SOURCE_ORIGIN,
SOURCE_AVAILABILITY in evidence.js)"*) and neither defines it. This is
consistent with `docs/ARCHITECTURE.md`, which says the client **carries the
Lumecon platform's own modules rather than describing them twice** — so the
authoritative enum lives in the Lumecon platform repository, which this machine
does not have.

**Observed values, and the only ones safe to emit:**

| field | values seen in the repo |
|---|---|
| `origin` | `"lumecon"` |
| `level` | `"entity"`, `"both"` |

`level` is documented in place: *"`level` says what the rows are: entity
records, or entity records that also roll up to geography."*

**RULE until the upstream enum is in hand:** emit only these three values. A
collection that needs a fourth is **BLOCKED, not free to invent one** — a
vocabulary member coined here is how two systems silently disagree, which is the
same failure shape as `tribe_id` carrying two identifier schemes and
`extent_competed` carrying two vocabularies.

**To close this:** read the Lumecon platform repo's `evidence.js`, or have the
enum stated. Until then `origin`/`level` are constrained, not validated, and the
distinction should travel with the descriptors.
