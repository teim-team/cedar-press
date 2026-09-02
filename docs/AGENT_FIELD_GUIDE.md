# AGENT FIELD GUIDE

*Written 2026-09-02. Every claim below was re-verified against the live files
that day; the file or script that proves each one is named. If you find one
stale, fix it here — a field guide repeating a stale claim is worse than none.*

**This is the short one.** `AGENTS.md` is ~6,000 lines and is mostly an
append-only journal of gate failures; `START_HERE.md` is ~1,000. Read those for
the dataset you are actually touching. Read *this* before you write anything,
once, in full. It is the set of traps that have each cost this project more
than one session.

---

## 0. Before you write anything

```
py -3 code/1050_preflight.py
```

It claims your script number atomically, prints which shared files need marker
discipline, reads `NEVER_RUN` live out of `cedar_pipeline.py`, and tells you how
to check whether the thing you are about to download is already on this
machine. Four commands, all read-only except `claim`:

```
py -3 code/1050_preflight.py claim <short_slug>   # take a number, atomically
py -3 code/1050_preflight.py ondisk <term>        # is it already local?
py -3 code/1050_preflight.py shared               # which files need markers
py -3 code/1050_preflight.py numbers              # the collision census
```

---

## 1. `ls code/<n>_*` cannot stop a collision. `claim` can.

43 numbers in `code/` carry more than one script; ten carry three. The
instruction to check first has been in `AGENTS.md` since 2026-08-07 and
`62_no_regression_check.py` has ratcheted `code_duplicate_numbers` at 43 since
2026-08-28. Neither made it shrink, because **check-then-write is not atomic**:
two agents both run `ls code/154_*`, both correctly see nothing, both write.

`1050_preflight.py claim` uses `os.open(..., O_CREAT|O_EXCL)`. The OS refuses
the second caller. It allocates strictly above the frontier, so a number is
never reused and a stale citation of "script 154" can never come to mean a
*new* script. Then write your code **into the stub it created** — do not create
a second file.

If you abandon the work: `py -3 code/1050_preflight.py release <n>_<slug>.py`.
It refuses to delete anything that is not still an untouched placeholder.

**Why the existing 43 are not being renamed** (measured 2026-09-02, so the next
agent does not re-open it): 43 numbers cover **96 files**; **40 of the 43** are
cited as "script N" in prose in `docs/` or the root `.md` files; and **417**
`.bak_*` files on disk are tagged with a bare number. Renaming is an owner
decision with a real blast radius, not an agent's cleanup. `claim` stops the
44th; the existing 43 are grandfathered by the ratchet in `62`.

**Backup tags carry the STEM, never the bare number.** `.bak_<date>_pre_1050_preflight`,
not `.bak_<date>_pre1050`. On 2026-08-26 four scripts were numbered 163, all
four wrote `.bak_2026-08-26_pre163`, and one of them restored by *glob* — which
reverted seven files belonging to two other agents and left the spine carrying
179 promoted NHOs whose ledger rows had just been deleted.
Full account: `review/_INCIDENT_2026-08-26_script163_number_collision.md`.
**Never restore by glob. Restore from a literal list of the files you wrote.**

---

## 2. Shared files: append inside your own marker, never rewrite

Some files are written **wholesale** by a generator that preserves only marked
blocks. Put your prose between your own pair and it survives; write outside
them and it is gone on the next run. Write over someone else's block and you
have destroyed their work — this already happened once to the Gaming section of
`docs/MONEY_TOTALLING_RULES.md`, which had to be restored from a commit, and
the marker convention is what came out of it.

```
<!-- BEGIN <YOUR-WORKSTREAM> -->
...
<!-- END <YOUR-WORKSTREAM> -->
```

Currently marker-protected (re-derive with `1050_preflight.py shared`, do not
trust this list to stay complete): `docs/MONEY_TOTALLING_RULES.md` (written by
`code/574_ws1_money_and_conservation.py`), `docs/ARCHITECTURE_DECISIONS.md`,
`docs/LABOR_SOURCES_FOR_GAMING_2026-08-26.md`.

The same problem in Python has the same shape: `code/512_build_dataset_contracts.py`
gives every workstream **its own `GRAIN_*` dict** (`GRAIN_WS2`, `GRAIN_FAADS`,
`GRAIN_GAMING`, …). Add yours; touch nobody else's.

Two blocks sharing a marker name are one block to the preserver. Pick a name
nobody has.

**Ownership is declared before you edit**, in `docs/ARCHITECTURE_DECISIONS.md`.
One agent owns a central file per pass. The integrator owns `62`, `512`, `517`,
`518` and **all commits**. No agent commits.

---

## 3. This repo's signature defect: a check that does not measure its own name

Fifteen measured instances. They share one shape — *the number was produced, it
was plausible, and it was about something else.*

| the check | what it reported | what it was actually measuring |
|---|---|---|
| `urllib.robotparser` | 22 sources "blocked" | a **403 on robots.txt** reads as `disallow_all`. A site that will not serve its robots file is not a site that forbids you. `docs/PULL_DISCIPLINE.md` |
| `27_build_dataset_manifests` | one gaming table at 17,877 rows | **physical lines**, against 1,521 CSV records — 11.8x, because quoted fields contain newlines. See its own docstring, line ~1404 |
| a `?wpdmdl=` harvester | 302 distinct documents, all HTTP 200 | **the same PDF 302 times**. Green statuses, one file. `docs/GAMING_SOURCE_AUDIT_2026-08-26.md` |
| `630_refresh_cadence` | event-driven sources scored stale | a **calendar** edge applied to sources that publish *when something happens* |
| `api.congress.gov` | 403 | **no User-Agent**, not an access restriction |
| `830_entity_freshness` | median 0 days, then median 6 | first **Cedar's own activity dates** won the max; then **future fiscal years were clamped to today** instead of discarded. It now discards them — see the docstring at line ~178 |
| `518` C4 | 47,877 rows with an attached identity | `owner_as_of_transaction_cedar_uid = "UNKNOWN"`. A populated cell is not a resolved identity |
| `518` C4 | percentages for `prime_contracts`, `subawards`, `faads_transactions*` | **estimates**: `SCAN_CAP = 50_000` rows per table. It now names them in `c4_sampled_tables` — read that field before quoting a C4 figure as a census |
| two, in one day, 2026-09-01 | a column match; a de-dupe | a regex matching `tract` inside `contract_number`; a de-dupe key that evaluated to `""` and would have matched **everything** |
| `845` regenerate guard v1 | 33 unsafe writers, worst at 62 and 53 columns | **name overlap, not the writer's actual output path.** `910`'s 62-column finding was an 11-column review file and `76`'s 27-column finding was a script that only READS that table - 9 of 29 findings were pairings that do not exist, while 26 real ones were invisible because the literal reached the writer as a `write_csv()` argument. A detector loud about nothing and silent about something. `code/845_regenerate_guard.py` |
| a regen-and-diff check | `docs/LOBBYING_BUILD_LOG_2026-08-05.md` PROVEN SAFE, byte-identical | **the generator never ran.** `06_build_log_stats_v2.py` exited 2 - it lives in `code/lobbying_pull/`, not `code/` - and an untouched doc is that check's strongest PASS. **Any regenerate-and-diff anywhere in this repo has this hole: assert the exit code before you read the diff.** `845 regen` now refuses on a nonzero exit |
| `845 scan_md` | 0 markdown docs at risk | **`git log` returned nothing**, so every doc scored 0 hand edits and the whole half printed clean. Seen from inside `62`, where the standalone run of the same code saw 9. It now RAISES rather than report a number it cannot measure, and `62` prints UNMEASURED |
| `845` class 3, first run | 13 sites UNDETERMINED, 6 of them wrongly | **`awards, stats = [], Counter()`** - a tuple bound to a tuple. The key set was fully knowable and the analyser could not see through the unpacking, so it reported *unmeasured* where the honest answer was *clean*. Undetermined is the safe direction to be wrong in, and it is still wrong |
| `845 regen`, "no digit = prose" | `docs/INVENTORY.md`, 20 hand-authored lines at risk | **blank lines and a repeated markdown table header.** A line with no digit in it is not a sentence somebody wrote. Replaced with the real measure - a removed line whose exact text appears NOWHERE in the rebuild - which is immune to reordering and to hunks that stop pairing |
| `845 regen`, default mode | *(caught before it ran)* | it invokes the generator **bare**, and `1020_tail_web_probe.py` writes its doc under `doc` while running a **network probe ladder** with no arguments. Regenerating that markdown would have opened sockets nobody asked for. It now refuses when the doc write sits behind a named subcommand, and takes the mode as an argument |

**The four habits that catch all fifteen:**

1. **A check does not count until a fixture proves it FIRES.** Inject the
   violation, assert exit 1 *and* that the NAMED invariant is what fired,
   restore, assert exit 0. A check that has never failed on purpose is not
   known to work.
2. **Verify your input contains what you think it does.** A check reading a key
   that does not exist passes for exactly the reason it is useless. Three
   instances in two days.
3. **Print the denominator, the sample cap, and one worked example row.** Every
   entry above would have died on sight next to a single real row.
4. **An absence of evidence must never print as evidence of absence.** Added
   2026-09-02, from two instances in one hour. A subprocess that did not run,
   a `git log` that returned nothing, a detector that could not resolve a
   name - each produced a CLEAN result, and clean is the strongest thing these
   checks can say. Check the exit code, check the input is non-empty, and emit
   **UNMEASURED** rather than a number. `62` already had this discipline for
   `293`; every new check needs it too.

---

## 4. Measure duplicates before you collapse them

Four of the five duplicate allegations investigated here were **phantom**:

| alleged | real | if collapsed |
|---|---:|---|
| `prime_contracts` | 80,778 → **0** | — |
| `faads_*` | 180,260 → **0** | would have destroyed **$8,291,124,113** of real obligations |
| `np_schedule_i_grants` | 101 → **0** | — |

A repeated *entity name* is not a repeated *transaction*. Two rows with the
same recipient and the same amount in the same year are usually two awards.
Find the discriminator column before you touch a row — `GRAIN_WS5` in `512`
records one that was found rather than assumed (`operating_company_seq`).
Evidence: `docs/FAADS_TRANSACTION_KEY_LOG.md`, `docs/methodology/contractors.md`.

---

## 5. "Missing" has four causes and only one is a download

At least three sessions have re-downloaded files that were already on this
machine. **27 of the 39** ranked absences in `docs/WHAT_IS_MISSING.md` are
`ON_DISK_NOT_PROMOTED`.

```
SOURCE_DOES_NOT_PUBLISH   a fact about the world. Never a Cedar deficiency.
ON_DISK_NOT_PROMOTED      already local. A join or a column list, NOT a fetch.
NOT_ACQUIRED              a real acquisition task.
CONSTRAINED               licence, statute or terms forbid it.
```

Name the state before you open a socket, and name it with a measurement:
`py -3 code/1050_preflight.py ondisk <term>` searches filenames *and* the live
column headers of `data/clean/` and `data/spine/`, because the usual shape of
the mistake is a column that exists in a clean table and is absent from the
sample a buyer was shown. `py -3 code/841_missing_probe.py` is the full ranked
measurement.

---

## 6. Numbers in this repo go stale in place

Superseded figures are never overwritten; they sit in the document where they
were written, looking exactly as authoritative as current ones.

- **`docs/DOC_CONTRADICTIONS_2026-08-26.md` outranks every build log** on any
  number they both state. Check it before quoting a figure.
- `STATE_OF_BUILD.md` and `STATE_OF_THE_LAND_2026-08-07.md` are the densest
  concentrations of superseded numbers in the project. Their *reasoning* is
  still good.
- **`NEVER_RUN` is live in `code/cedar_pipeline.py` and is the only authority.**
  As of 2026-09-01 it contains **one** script — `41_build_codebooks.py`.
  `01_build_entity_spine.py`, `09_import_rulings.py` and
  `88_build_deals_taxonomy.py` came *off* the list, proven safe by
  `code/812_c8_rebuild_proof.py`. Any prose still calling those three "unsafe to
  run" is stale. Before any rebuild: `py -3 code/build.py plan <collection>`.
- `mtime` answers freshness. It says nothing about completeness.

---

## 7. The standing gates

| command | what it holds |
|---|---|
| `py -3 code/1050_preflight.py` | before you write |
| `py -3 code/293_lint_bug_classes.py` | the seven named defect classes. **The single lint entry point** — `248` is a retired stub. `--selftest` proves the detectors still fire |
| `py -3 code/62_no_regression_check.py` | the ratchets, including `code_duplicate_numbers` |
| `py -3 code/518_dataset_readiness.py` | READY / BLOCKED / NOT_TESTED per dataset. **There is no fourth status** |
| `py -3 code/287_build_dependency_manifest.py` | which script rebuilds a file another script enriches. The enricher runs LAST |

**Never re-baseline to clear a red gate.** `--baseline` records a floor while
GREEN. A gate you stepped around is a gate the next six sessions also step
around.

**A red gate is not automatically yours.** Name the owner with a measurement —
which table moved, by how many rows, and which script wrote it — the way the
gate-failure entries in `AGENTS.md` do. Then say so in writing.
