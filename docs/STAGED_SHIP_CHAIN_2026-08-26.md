# The ship chain is STAGED, not run — 2026-08-26 ~21:15

*Written by `code/391_triage_unshipped_tables.py` and
`code/392_write_unshipped_codebook_fragments.py`. Read
`docs/SHIPPING_RUNBOOK.md` first; this is what changed, and what is left.*

---

## 1. WHY IT IS STAGED

`87` rewrites every dataset's notes contract and `25` rebuilds the whole
publication layer. Both read `data/clean` end to end, so a live writer means a
partial artefact that looks complete. `Win32_Process` was checked before the
registration work and again before deciding, and the window never opened:

| time | live | writing |
|---|---|---|
| 20:31 | `121_pull_subawards_api.py pull --sequential` | raw subawards |
| 20:31 | `317_cdx_tribal_vendor_hosts.py` | vendor-host harvest |
| 20:31 | `327_migrate_class7_keys_to_digests.py` | **keys, in place, across clean tables** |
| 20:31 | `367_courtlistener_party_name_probe.py` | adjudication probe |
| 20:55 | `384_crawl_uncrawled_open_properties.py discover` | property site corpus |
| 20:55 | three concurrent `62_no_regression_check.py`, one `293 --class 6` | — |

`data/clean/*.csv` was last written at **20:24:46**
(`lobbying_issue_families_filing.csv`,
`lobbying_registrant_client_relationships.csv`,
`cedar_correction_register.csv`) — inside the runbook's own 30-minute stop
rule — and `327` relaunched twice during the session. A further table,
`cedar_entity_identity_crosswalk.csv` (10,107 rows), **landed after the triage
snapshot was taken** and is named in §7.

**The registration work was done. The chain was not started.**

---

## 2. WHAT WAS DONE, AND WHY IT IS SAFE WITH WRITERS LIVE

Everything below writes metadata about tables. **Not one data row was written.**

1. **`391_triage_unshipped_tables.py`** — a verdict for every zero-ship table,
   into `docs/UNSHIPPED_TABLE_TRIAGE.json` / `.md`. Writes only to `docs/`.
2. **`392_write_unshipped_codebook_fragments.py`** — **73 codebook fragments**,
   one file per block, under `data/clean/codebook/`. A fragment is the one file
   a dataset owns alone, so two agents writing different datasets cannot
   collide. **`codebook_master.csv` is never opened for writing by 392.**
3. **`cedar_codebook.INTERNAL_TABLES`** — 56 deliberate non-ships, each with
   its reason. An additive constant plus one `continue` branch.
4. **`87_build_dataset_notes.py`** — the internal gate wired in, plus one
   corrected line (§5).
5. **`py -3 code/cedar_codebook.py build`** — RUN. Step 1 of the chain, and it
   writes exactly one derived file, `codebook_master.csv`, atomically
   (`.tmp` then replace), from the fragments. **2,798 → 4,465 rows.** Backups:
   `graveyard/2026-08-26_pre_391_392_registration/codebook_master.csv` and
   `data/clean/codebook_master.csv.bak_2026-08-26_prefragment`.

Registry effect, from `cedar_codebook.registered_tables()`:

| | before | after |
|---|---:|---:|
| shippable | 128 | **198** |
| undocumented | 140 | **15** |
| licensed, never ships | 2 | 2 |
| internal by decision | — | **56** |

And from `62_no_regression_check.py`, which was run before and after:

| metric | before (20:36) | after (21:00) |
|---|---:|---:|
| `codebook_variables` | 2,798 | **4,465** |
| `tables_missing_codebook_block` | 139 | **67** |
| `codebook_undocumented_public` | 0 | **0** |
| `duns_marked_publishable` | 0 | **0** |
| `ship_ratio_pct` | 86.917 | 86.917 — *moves only when 87 and 25 run* |
| `ship_tables_at_zero` | 138 | 138 — *same* |

`62`'s 67 is larger than the registry's 15 because `62` counts by its own glob
and does not yet subtract `INTERNAL_TABLES`: 15 undocumented + 54 of the 56
internal (two of which now match a sibling block and are held out by the gate
in `87` instead). **That counter is a gate metric owned by the gate; it was not
touched, and it fell rather than rose.**

---

## 3. WHAT IS LEFT. RUN THIS, IN THIS ORDER, IN A QUIET WINDOW

Step 1 is already done and is idempotent; re-running costs nothing.

```
# 0. the window test - ALL of it, not just the first line
ls -l --time-style=full-iso data/clean/*.csv | sort -k6 | tail -20
ls logs/_HOSTLOCK_*.json
#   and, because a dead wrapper is not a dead poller:
#   Get-CimInstance Win32_Process -Filter "Name='python.exe' OR Name='py.exe'"
#   If any data/clean/*.csv changed in the last 30 minutes, STOP.

mkdir -p graveyard/$(date +%F)_pre_ship
cp -r dist graveyard/$(date +%F)_pre_ship/dist

py -3 code/cedar_codebook.py build      # 1. done 2026-08-26; idempotent
py -3 code/62_no_regression_check.py    # 2. see §4 - a KNOWN, OWNED failure
py -3 code/87_build_dataset_notes.py    # 3. read SHIP RATE, NOT SHIPPED,
                                        #    INTERNAL BY DECISION, LICENCE GATE
py -3 code/102_build_coverage_profile.py
py -3 code/110_build_harmonized_views.py
py -3 code/25_build_publication_layer.py
py -3 code/27_build_dataset_manifests.py
```

### `87` WAS PROVEN TO WORK BEFORE BEING LEFT UNRUN

`87` was executed end to end with its `DIST` constant redirected to a scratch
directory, so **not one file under `dist/` was written** and the real chain
stays staged. It exited 0 and printed:

```
LICENCE GATE - 2 file(s) REFUSED, by name
INTERNAL BY DECISION - 56 table(s) ... NOT part of the backlog below
NOT SHIPPED - 14 clean table(s) have no codebook block at >=0.60
 199  notes written
  56  internal by decision, not a shipping gap
  14  skipped: not a documented dataset
   2  REFUSED: vendor-licensed, may never ship

SHIP RATE: 8,463,350 of 8,467,275 rows in data/clean reached a notes
           contract  (99.954%)
           3,925 rows are in data/clean and in no bundle.
```

**199 notes contracts against 128 before; 14 unshipped tables against 139.**
The ledger carries the new `INTERNAL_BY_DECISION` fate on 56 rows and **zero**
rows reading `-1`, where every one of the 140 did before.

**Note the resolution.** The rate is printed to three decimals now, not one:
at one decimal a genuine 99.954% and the old arithmetic bug BOTH read
`100.0%`, so fixing the bug would have looked like changing nothing. A meter
whose resolution hides the last mile fails the same way as a meter reading
zero.

**This is registration, not shipment.** 87's rate answers "does this table have
a contract to leave under". `62`'s `ship_ratio_pct` answers "is it on the
shelf", and that one does not move until `25` has run.

### What `87` must print, or something is wrong

- **`LICENCE GATE - 2 file(s) REFUSED, by name`** — `gaming_facility_metrics.csv`
  and `gaming_property_capacity_history.csv`. **If this line is absent the gate
  is dead again.** It was dead for twenty days once.
- **`INTERNAL BY DECISION - 56 table(s)`**, by name. New. These are NOT the
  backlog.
- **`NOT SHIPPED`** — expect **14**, not 139: the 11 refused for thin
  documentation (§6), plus `gaming_property_locations.csv`,
  `consultation_agency_coverage.csv` and `wa_machine_transfers.csv`.
- **`SHIP RATE`** — **99.954%**, printed to three decimals, with **3,925**
  rows named as unshipped. See §5 for why every earlier run said `100.0%`.

### After the chain: four stale notes contracts to delete

Four tables move out of a block that never described them and into one written
from their own header. `87` writes the new contract; it does not remove the old
one, and `160` will report the duplicate.

```
dist/06_nonprofit/bill_votes_entity_bridge.notes.json      + .NOTES.md
dist/09_federal_actions/fr_consultation_notices.notes.json + .NOTES.md
dist/11_nagpra/fr_consultation_referenced.notes.json       + .NOTES.md
dist/16_digital_gaming/loyalty_program_property.notes.json + .NOTES.md
```

Delete by **exact filename**. Never by glob — concurrency rule 2.

---

## 4. `62` FAILS, IT IS NOT THIS PASS, AND IT MUST NOT BE RE-BASELINED

Measured three times across the session. Every failing finding is another
agent's script, two of which were running at the time:

| run | failing finding | owner |
|---|---|---|
| 20:36 (before) | `class2c 382_remine_property_site_corpus.py: stats["capacity_refused_implausible"] += 1` | property-site re-mining pass, LIVE |
| 21:00 | `class2c 384_crawl_uncrawled_open_properties.py: stats["hosts_stopped_on_first_refusal"] += 1` | open-property crawl, LIVE |
| 21:00 | `class6 98_build_oira_and_hearings.py: hearing_appearances.csv` | OIRA/hearings build |
| 21:15 (final) | `class6 97_build_aliases_and_relationships.py: entity_aliases.csv` | alias/relationship build |

By the final run the two `class2c` findings were gone — their owners fixed
them — and `class2c` was back at its floor of 60.

**`class7` is 42 before, 42 after, 42 final.** The tracked gate metric did not
move. **Neither `391` nor `392` appears in any `293` finding, in any run.**

Four registry metrics also rose by **exactly one** between the 21:00 and 21:15
runs — `ship_tables_at_zero` 138 → 139, `tables_missing_from_25_TABLES`
234 → 235, `tables_missing_from_27_SPEC` 249 → 250,
`tables_missing_notes_contract` 139 → 140. `62` names the cause itself:

```
NEW TABLES AT A 0% SHIP RATIO (1), not in the shipping baseline:
  - cedar_entity_identity_crosswalk.csv (10,107 rows)
```

**That is one table another agent landed during the session, not a
regression in this pass.** `ship_ratio_pct` moved 86.917 → 86.811 for the same
reason: the warehouse grew, the shelf did not. Registration moved
`tables_missing_codebook_block` **139 → 69** across the same window.

Standing rule 15 says name it and its owner rather than stepping around it;
that is done here and in `AGENTS.md`. **Do not run `62 --baseline` to make it
green.** A floor recorded over a live failure buries every other regression
behind it — which is exactly what six sessions in a row did with
`codebook_undocumented_public = 45`.

---

## 5. `87`'s SHIP RATE WAS 100.0% AND IT WAS A BUG

`87` read:

```python
n_lost, _, _, _, _ = scan(CLEAN / name)      # scan() returns EIGHT values
```

The `ValueError` was caught by the `except Exception` under it, so `n_lost`
became `-1` for **every** unshipped file, `lost_rows` never left 0, and

```python
rate = shipped_rows / (shipped_rows + lost_rows)
```

printed **shipped-of-shipped — 100.0%, every run.** Confirmed in the artefact
before the fix: all **140** `NO_CODEBOOK` rows of `dist/_ship_rate.csv` carry
`rows = -1`.

It is the shape this very script was rewritten to stop — *a drop ledger that
cannot say what it dropped* — turned on itself. Fixed by taking element 0 **by
index**, so a future change to `scan()`'s return cannot silently zero it again,
and by printing the failure instead of swallowing it.

Measured after the fix, on a scratch `DIST`: **99.954%** — 8,463,350 of
8,467,275 rows — with **3,925 rows named**, against a ledger where all 140
unshipped files previously read `-1`. **The number barely moved and the meter
changed completely**, which is why it is now printed to three decimals: at one
decimal the bug and the truth are the same string.

The other project-wide figure, `62`'s `ship_ratio_pct` = **86.811%**, was never
broken and measures something different — rows actually in `dist/`, not rows
with a contract. It moves only once `25` has run.

`_ship_rate.csv` also gains a third fate, `INTERNAL_BY_DECISION`, which is
listed by name and kept OUT of the denominator. A ratio that can never reach
100% is a ratio nobody reads.

---

## 6. ELEVEN TABLES REFUSED FOR THIN DOCUMENTATION — a writing task

Not a defect and not a gap: these are tables whose columns nobody has ever
defined. `392` refuses to register a block that would define fewer than 8
variables AND under 60% of the columns 41 would publish, because a notes
contract listing two of eleven columns is a dataset that *looks* documented.

| table | rows | defined / publishable |
|---|---:|---|
| `agency_attention_vs_advocacy_year.csv` | 698 | 1 of 4 |
| `lobbying_issue_family_year.csv` | 476 | 5 of 9 |
| `tcu_cdfi_ownership_evidence.csv` | 130 | 2 of 6 |
| `lobbying_target_entities.csv` | 116 | 1 of 3 |
| `grantmaker_funding_overlap.csv` | 69 | 4 of 12 |
| `tcu_roster.csv` | 37 | 6 of 12 |
| `inflation_deflator.csv` | 27 | 3 of 6 |
| `lobbying_disclosure_verbosity_year.csv` | 27 | 2 of 4 |
| `gaming_mitigation_agreements.csv` | 24 | 7 of 18 |
| `agency_attention_vs_advocacy.csv` | 22 | **0 of 9** |
| `fr_consultation_by_agency.csv` | 21 | 1 of 3 |

**1,647 rows.** Six are `78_content_analysis.py` series and
`docs/CONTENT_ANALYSIS.md` explains in prose what each measures — write those
definitions into `docs/codebooks/` as a markdown table and re-run `392`, which
picks that directory up automatically.

**And note what registration did NOT do.** 642 columns across the 73 registered
blocks have no definition anywhere and are written `published = 0`,
`access_tier = internal`, with a description that says exactly that. They are
withheld, not guessed at. `docs/UNSHIPPED_CODEBOOK_REGISTRATION.json` carries
the defined-share for every registered table. **A block makes a table
shippable; it does not make it documented**, and this project has confused the
two before (`nigc_declination_letters.csv`, 45 of 60 variables undefined).

### The tier finding that came out of this, and it is worth keeping

**A DEFINITION AND A TIER MUST NOT CONTRADICT EACH OTHER.** `identifier` is
`access_tier = internal` in **eight** codebook blocks and `public` in one, and
its written definition begins *"WITHHELD from publication."*
`41.access_tier("identifier")` nevertheless returns `public`, because the bare
name misses its `IDENTIFIER_COLS` regex. The first run of `392` therefore wrote
`identifier` into the ledger block as **published, carrying a description that
says it is withheld** — and it would have shipped that way.

Two guards now stand in `392`, and the fragments were deleted by exact filename
and rewritten under both:

1. **Unanimous inheritance.** 235 column names are tiered internal by EVERY
   block that carries them. That tier is inherited, never re-decided here —
   AGENTS.md rule 1, applied to the codebook itself.
2. **The contradiction guard.** A definition matching `WITHHELD` or
   `never publish` forces `internal` regardless of what the regex says. The
   prose wins: somebody wrote it deliberately, and a regex did not.

---

## 7. FOUR QUESTIONS FOR A PERSON

| table | rows | the question |
|---|---:|---|
| `gaming_property_locations.csv` | 2,212 | The runbook says it ships only its `publishable = Y` rows — 741 are `N` — and **no script applies that filter**. Who applies it: `143` at build time, or the bundler? Registering a block would decide it by default and put all 2,212 rows in a notes contract. |
| `consultation_agency_coverage.csv` | 66 | Half its columns are findings about AGENCIES (does each publish named participants, locations, dates; what its consultation policy obliges) and half are counts of what we collected. Split it, or ship it with the coverage columns internal? |
| `cedar_correction_register.csv` | 163 | Owned by the live lobbying-correction pass, scripts 350-358, which registered its own block at 20:35 during this session. Their call, not mine. |
| `cedar_entity_identity_crosswalk.csv` | 10,107 | **Landed after this triage was taken** and has no verdict. `391` names it and exits non-zero rather than calling the triage complete. Whoever built it should rule it — and note that "extract the entity crosswalk as a standalone deliverable" is the one thing `87`'s TERMS forbid a subscriber to do. |
