# Shipping runbook

*Written 2026-08-26 alongside `docs/GAMING_SOURCE_AUDIT_2026-08-26.md`, which
found the gaming collection shipping **912 of 104,412 rows — 0.87%** — because
this chain had not been run since 2026-08-06 and silently dropped everything it
could not match.*

**The chain is STAGED, NOT RUN.** Two agents were live when this was written:
one rebuilding the gaming collection against NIGC and state regulators
(`gaming_facilities.csv` moved 774 → 784 and `gaming_facility_metrics.csv`
65,223 → 68,211 during the audit itself), one rebuilding `coverage_audit.csv`
via script 102. **Rebuilding `dist/` from data that is concurrently changing is
how this project lost work before.** Do not start until both are done.

---

## 0. BEFORE YOU START — three checks, all cheap

```
# a. is anyone still writing?
ls -l --time-style=full-iso data/clean/*.csv | sort -k6 | tail -20
ls logs/_HOSTLOCK_*.json 2>/dev/null

# b. is the codebook still whole? (read-only, must print SAFE)
py -3 code/cedar_codebook.py check

# c. back up what the chain overwrites
mkdir -p graveyard/$(date +%F)_pre_ship
cp data/clean/codebook_master.csv graveyard/$(date +%F)_pre_ship/
cp -r data/clean/codebook          graveyard/$(date +%F)_pre_ship/fragments
cp -r dist                         graveyard/$(date +%F)_pre_ship/dist
```

**If any `data/clean/*.csv` has changed in the last 30 minutes, stop.** The
gaming agent writes there.

---

## 1. THE ORDER, AND WHY IT IS THIS ORDER

Run these one at a time. Read the output of each before starting the next —
every one of them now names what it drops, which is the entire point of the
2026-08-26 changes.

| # | command | what it does | what to read in the output |
|---|---|---|---|
| 1 | `py -3 code/cedar_codebook.py build` | fragments → `codebook_master.csv` | must say `ADDS`, never `REFUSING` |
| 2 | `py -3 code/62_no_regression_check.py` | the gate. Nothing ships past a regression | any `FAIL` stops the chain |
| 3 | `py -3 code/87_build_dataset_notes.py` | notes contract per dataset | **`SHIP RATE:`** and the `NOT SHIPPED` list |
| 4 | `py -3 code/102_build_coverage_profile.py` | source coverage profile | — |
| 5 | `py -3 code/110_build_harmonized_views.py` | harmonised views | — |
| 6 | `py -3 code/25_build_publication_layer.py` | `cedar_press.db`, `.xlsx`, sanity | **`SHIP RATE:`**, `[licensed]` drops, `FAIL` sanity checks |
| 7 | `py -3 code/27_build_dataset_manifests.py` | app manifests | **`NO MANIFEST`** list, `manifest coverage:` |

**Why 1 first.** `87` reads `codebook_master.csv`. If the master is stale, every
dataset registered since is silently skipped — that is the original defect.

**Why 2 before 3.** A notes contract asserts row counts. Asserting counts that
have regressed publishes the regression.

**Why 6 after 3.** `25`'s table list is now derived from the same codebook
registry `87` uses (`cedar_codebook.registered_tables()`). Running it against a
stale master reproduces the bug in the database instead of the notes.

**NEVER run `41_build_codebooks.py`.** It writes `codebook_master.csv` in `"w"`
mode from a hardcoded 19-group `DATASETS` dict. Running it today deletes **21 of
the 43** dataset blocks, including every block registered on 2026-08-26. If you
need to regenerate a block, use `cedar_register_codebook.py` or write the
fragment directly — never 41. This is the single most destructive command in the
repo and its name does not say so.

---

## 2. WHAT "GOOD" LOOKS LIKE

After step 3 (`87`):

- **`SHIP RATE:` well above 0.87%.** The audit measured the gaming collection at
  0.87%; the registrations on 2026-08-26 unblocked 18,973 gaming rows and the
  registry now resolves 107 shippable tables against 26 previously hardcoded.
- **`LICENCE GATE - 2 file(s) REFUSED, by name`** — `gaming_facility_metrics.csv`
  and `gaming_property_capacity_history.csv`. If this line is absent the gate
  has been broken again; it was dead for twenty days once already.
- **`NOT SHIPPED`** lists every clean table with no codebook block, by name and
  score. This list is the backlog, not an error. It should shrink between runs.
- **`[undefined]`** names tables shipping variables with no description.
  `nigc_declination_letters.csv` will appear: **45 of its 60 public variables
  have no written definition**, because `docs/codebooks/07d_nigc_declination_variables.md`
  documents only the 13 columns script 100 added, not the 47 script 91 built.
  **Registering a block made it shippable; it did not make it documented.**
  Either write those definitions or tier the columns internal before this one
  goes to a subscriber.

After step 6 (`25`):

- **`[licensed] ...: dropping recipient_duns`** on `funding_transactions`. The
  previous database shipped **404,236 populated DUNS** against terms of use that
  say DUNS is never published. If that line does not appear, the strip is broken.
- **`[licensed] gaming_facilities: dropping casino_city_id`** — 595 populated.
- Sanity checks: **zero FAIL**.

After step 7 (`27`):

- **`manifest coverage:`** — expect it to be low and honest. A manifest states
  what a dataset *measures*, which is an authored claim and is never generated.
  The `NO MANIFEST` list is the writing backlog.

---

## 3. IF SOMETHING GOES WRONG

| symptom | cause | fix |
|---|---|---|
| `cedar_codebook.py build` prints `REFUSING` | a fragment failed to write, or a block exists only in the master | `py -3 code/cedar_register_codebook.py reconcile` — it writes the missing fragments one at a time. **Do not use `--force`** until `check` prints `SAFE`. |
| `build` raises on unexpected keys | a fragment with a non-standard schema | `reconcile` normalises it. `02b_subawards_api.csv` was the known one (9 cols vs 10). |
| a dataset you expected is in `NOT SHIPPED` | no codebook block, or a stub block | check the score. Under ~0.25 usually means a **stub** — `07j`/`07k`/`07l` documented 6, 2 and 5 columns of 26, 23 and 31. A stub can never reach 0.60. |
| `87` writes a contract for a licensed file | the gate is dead again | `LICENSED_SOURCE_FILES` must be *referenced* in `main()`, not merely declared. It was declared and unreferenced from 2026-08-06 to 2026-08-26. |
| the DB is missing gaming tables | master is stale | run step 1 first. |

**Rollback.** Everything the chain writes is in `dist/`. Restore from the
`graveyard/<date>_pre_ship/dist` copy made in step 0.

---

## 4. THE BACKLOG THIS CHAIN WILL NAME

Known and expected in the `NOT SHIPPED` list on the next run — these need a
codebook block written, and are ranked in
`docs/GAMING_SOURCE_AUDIT_2026-08-26.md` Part 5:

| table | rows | note |
|---|---:|---|
| `gaming_game_finder_observations.csv` | 6,851 | stub fragment, 5 of 31 columns |
| `gaming_property_locations.csv` | 2,212 | **also needs a row filter — 741 rows are `publishable = N`** |
| `fac_audit_gaming_disclosures.csv` | 1,521 | |
| `gaming_properties.csv` | 784 | the de-vendored replacement for `gaming_facilities` |
| `gaming_property_federal_traces.csv` | 774 | |
| `gaming_property_coverage.csv` | 774 | |
| `gaming_vendor_tribal_licenses.csv` | 740 | |
| `gaming_nigc_roster_link.csv` | 442 | built by the concurrent agent 2026-08-26 |
| `gaming_financing_events.csv` | 293 | |
| `gaming_property_site_observations.csv` | 262 | stub fragment, 6 of 26 columns |
| `gaming_source_claims.csv` | 113 | |
| others | ~400 | |

---

## 5. THE STANDING RULE THIS REPLACES

There was no rule. `AGENTS.md` mentioned script 87 once, in passing, in a
sentence about where presentation lives. The shipping step was written down
exactly once — `docs/handoffs/STATE_OF_THE_LAND_2026-08-07.md` §7, item **6 of 6** — and
carried forward unread through twenty days and roughly twenty builds.

**A build is not finished when the table is written. It is finished when the
table can leave the building, or when a named line says why it cannot.**


---

## 6. UPDATE 2026-08-26 ~21:00 — the backlog in Part 4 is registered; the chain is still staged

**74 codebook blocks were written** (`code/391_triage_unshipped_tables.py`,
`code/392_write_unshipped_codebook_fragments.py`), covering **488,109 rows**
including every gaming table listed in Part 4 above. `codebook_master.csv` was
rebuilt from fragments — **step 1 only** — taking the registry from 128
shippable tables to **199**, and the undocumented list from 140 to **13**.

**Steps 2-7 have NOT been run.** No quiet window opened: `327_migrate_class7_
keys_to_digests.py` was rewriting keys in place, `384_crawl_uncrawled_open_
properties.py` was crawling, `121` was pulling subawards, and `data/clean` was
last written at 20:24, inside the 30-minute stop rule in Part 0 above.

Three things that change what Part 2 tells you to expect:

- **`NOT SHIPPED` should now list 13 tables, not 139.** 56 of the old 139 are
  declared in `cedar_codebook.INTERNAL_TABLES` and appear under a new
  **`INTERNAL BY DECISION`** heading instead. They are a decision, not a gap.
- **`SHIP RATE` was printing 100.0% and was wrong.** `87` unpacked five values
  from `scan()`, which returns eight; the ValueError was swallowed and
  `lost_rows` never left zero. Fixed. The next figure will be far lower and
  will be the first honest one.
- **Four notes contracts must be deleted after the run**, by exact filename —
  four tables move out of a block that never described them. The list is in
  `docs/STAGED_SHIP_CHAIN_2026-08-26.md` Part 3.

**Everything left to run, and what each line must print, is in
`docs/STAGED_SHIP_CHAIN_2026-08-26.md`.** Read Part 4 of it before treating
`62`'s red as yours.
