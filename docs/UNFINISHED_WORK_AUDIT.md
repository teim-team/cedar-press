# Unfinished work audit — the 52 scripts that declare an output that does not exist

*Written 2026-08-26 by `407_unfinished_work_audit`. Inputs:
`docs/SHIP_GAP_REPORT.json` run 3 (generated 20:28), read at
`docs/SHIP_GAP_REPORT.json.bak_2026-08-26_pre_407_unfinished_work_audit`.*

**Scope:** the 52 scripts the detector filed `OUTPUT_MISSING` plus the 1 it filed
`NEVER_RUN` — 53 in all. Every one is dispositioned by name below.

---

## THE HEADLINE, AND IT IS NOT THE ONE THE TASK EXPECTED

**45 of the 53 were the detector's own fragments, not the project's gaps.** Not
one of them was a script that had been started and dropped; they were filenames
the extractor cut in half, files that exist two directories outside the index,
API endpoints quoted in citations, and — four times — **files whose absence is
the SUCCESS condition**, because the script deletes them or writes them only
when a check fails.

That is an **85% false-positive rate on the strongest verdict this report
issues**, and it matters more than the eight real findings underneath it. The
work queue's own diagnosis of the 0.87% ship rate is that failures survive
because nobody reads the thing that would have caught them. A detector that
names 53 scripts and is wrong about 45 of them is a detector that gets skimmed,
and the eight real ones ride out on the noise. **The false positives were fixed
at source, in `code/160_ship_gap_report.py`** — see "What was fixed" below.

The sole `NEVER_RUN` verdict in the whole report — `90_build_review_page.py` —
was **entirely spurious**. Its one declared path was
`a.download='cedar_rulings___DATE__.csv'`, a filename handed to a *browser* for a
client-side save. The report's most alarming single verdict pointed at a string
that never becomes a file on this machine.

| disposition | n |
|---|---:|
| **FALSE POSITIVE** — stale declaration, fixed at source | **45** |
| **STILL WANTED** — real unfinished work | **7** |
| **TRUE SIGNAL, no work owed by this script** — declares a never-run script's output as an input | **1** |
| **RUN BUT FAILED SILENTLY** | 1 *(within STILL WANTED: `211`)* |
| **SUPERSEDED** | 1 *(within STILL WANTED: `101`'s employment leg, by `100`)* |
| **ABANDONED BY DESIGN, verified** | 3 *(within FALSE POSITIVE: `83`×2, `36_build_nho_intertribal`)* |
| **OUTPUT RENAMED** | 1 *(within FALSE POSITIVE: `73`)* |

**Detector, before → after: `scripts_output_missing` 52 → 10, `scripts_never_run`
1 → 0.** Of the 10 that remain, 8 are the genuine findings below and 2
(`319_load_tribal_vendor_list_verdicts.py`,
`384_crawl_uncrawled_open_properties.py`) are live agents' scripts written after
run 3 and are not in scope here.

---

## 1. STILL WANTED — ranked by value

**None of the seven was run.** Not one is blocked on doubt about whether it
should be; every one is blocked on a host lock held by a live process, a spent
API budget, or an input a human has to write. That is the honest answer to *"do
the cheap, unambiguous ones"* — the cheap ones were the 45 false positives, and
they are done. Each entry below states its unblock condition, because a queue
entry that does not say what it is waiting on becomes a queue entry that waits
forever.

### 1. `40_contracts_ledger_pass.py` — NEVER RUN. Measures a hole the project currently only asserts.

**Value: highest.** Four USAspending socio-economic flag values —
`indian_tribe_federally_recognized`, `us_tribal_government`,
`housing_authorities_public_tribal`, `tribal_college` — **return ZERO as filter
values even though they exist as populated output columns**. So a tribal
government contracting *in its own name* is invisible to the Pass A route in
`code/37`. This pass queries by the ledger's own tier-A UEIs instead, which
depends on no flag being set, and the difference between the two **is the size
of the hole, measured rather than asserted**. It bears directly on the $65.24B
unattributed prime tail and on the 79.0% attribution rate in `START_HERE.md`.

Evidence it never ran: no `logs/40_contracts_ledger_pass.log`, no
`review/contract_ledger_pass_tierA_2026-08-05.csv`, no
`_ledger_pass_state.json` checkpoint. Script number 40 collides three ways
(`40_build_prime_contracts.py`, `40_contracts_ledger_pass.py`,
`40_pull_usaspending_subawards.py`) so the detector suppressed log evidence and
could not say this; the named log file simply is not there.

**Blocked on:** the `api.usaspending.gov` host lock, held by live
`121_pull_subawards_api.py pull --sequential` (PID 13736, collect deadline
2026-08-27T05:19Z).
**Effort:** none in code. One unattended run, resumable via its checkpoint.
**Do not raise `BATCH` above 20** — 21+ values returns HTTP 503, not a clean 400.

### 2. `67_sam_entity_harvest.py` — NEVER RUN. The only exact route to the EIN↔UEI join, gated on one un-run function.

**Value: very high.** `extract()` opens with
`raise SystemExit("run --discover first; codes are not hard-coded")`, and
`--discover` has never written `data/raw/.../sam_business_type_codes.csv`. So the
whole leg is stopped by one function that was never called. Work-queue item 2
measured the IRS hypothesis to essentially zero — **28 of 12,764 `np_orgs` EINs
(0.22%) reach a spending UEI** — and concluded that *"the only exact route is
the SAM entity-management extract"*. This is that extract. It also serves the
tribal-certification work, which targets the project's weakest evidence class:
almost all ownership evidence held today is self-certification.

**Blocked on:** the SAM 10/day quota. 8 of 10 calls are spent today, and
`START_HERE.md` reserves **tomorrow's first six** for
`141_pull_sam_contract_awards.py download` — those six export tokens are already
paid for and a submission is not retryable, so they outrank this. Genuinely
unblocked only by the **role request (10/day → 1,000/day)**, which also unblocks
subawards FY2021–24.
**Effort:** 1 call for `--discover`, then one call per Native business-type code.

### 3. `211_cdx_enumerate_blocked_gaming_hosts.py` — **RUN BUT FAILED SILENTLY. It was killed, and it left no checkpoint.**

**Value: high, and this is the one finding the detector could not have reached.**
`logs/211_cdx_bypass.log` is **166 bytes** and stops mid-enumeration:

```
  gaming.az.gov: enumerating ...
    gaming.az.gov: page 1, +20001 -> 20000
    gaming.az.gov: page 2, +20001 -> 40000
    gaming.az.gov: page 3, +20001 -> 60000
```

The `_cdx_state.json` write sits inside a `finally:` block, alongside
`release_lock()`. **A `finally:` block that did not execute means the process was
killed, not that it failed** — an exception would still have written the state.
So: no checkpoint, none of the `cdx_<host>.json` outputs landed, and **a resume
restarts from zero after three pages of a 60,000-capture sweep.**

This is the only route into `gaming.az.gov` and `www.nmgcb.org`, both 403 behind
Cloudflare, and work-queue item 9 calls NM quarterly per-tribe revenue sharing
and AZ per-tribe contributions **"the highest-value unworked series"**.

**Blocked on:** the `web.archive.org` host lock, held by live
`317_cdx_tribal_vendor_hosts.py` (PID 6568, claimed 2026-08-26T23:53Z, 2h
deadline) with 49 hosts queued behind it. *(The stale-lock note in
`docs/WORK_QUEUE.md` — "PID 7420 dead since 2026-08-07" — is now **out of date**:
the lock was taken over legitimately by 213 and then by 317.)*
**Effort:** ~2h unattended once the lock frees.
**Earned rule:** *a checkpoint written only in `finally:` is not a checkpoint —
`finally:` does not survive a kill.* Write the state file after each page.

### 4. `83_build_resource_ledger.py` — the Navajo audited-actuals harvest was never done.

**Value: medium-high.** `build_navajo()` reads
`data/raw/resources/new_mexico/cedar_navajo_audited_actuals.csv` and returns
immediately if it is absent, which it is. **The parser is shipped and the data
was never harvested** —
`docs/RESOURCE_LEDGER_STATES_LOG.md` item 3 says exactly that: *"the parser is
shipped; harvest the remaining years from `dibb.nnols.org`"*. Navajo is the
largest single resource-revenue entity in the corpus, so the ledger is short by
its biggest contributor's audited figures.

**Blocked on:** a network harvest from `dibb.nnols.org` under a fresh host lock.
**Effort:** harvest only; no code. **Note:** the script's *other* two absent
paths are NOT gaps — see §3.

### 5. `289_update_collection.py` — NEVER RUN for real. Dry-run only.

**Value: high in principle, but this is already queued.** The only log is
`289_dryrun_2026-08-26.log`, and no `_MANIFEST.json` exists anywhere under
`dist/` — that file is the snapshot-and-rollback record written at the start of a
real update, so its absence proves no real update has happened. This is
**`docs/WORK_QUEUE.md` item 4, the shipping chain**, and it is the thing that
would actually move `ship_ratio_pct` (86.917% today). Listed for completeness,
not as new work.

**Blocked on:** *"Only when no writer is live"* — five are (`121`, `317`, `367`,
`327`, plus the property-site crawler).
**Effort:** the full chain, `cedar_codebook.py build` → `62` → `87` → `102` →
`110` → `25` → `27`.

### 6. `107b_fill_source_urls.py` — NEVER RUN. **This is the `122` shape: the promised input was never written.**

**Value: medium — it closes a REPRODUCIBILITY gap, not a coverage one.**
`docs/STATE_GAMING_PULL_LOG.md` promises the step in the same words 122's
docstring used: *"drop a `_retriever_urls.csv` (`relative_path, source_url,
fetched_date, note`) beside the manifest and run it"*. **It was never dropped.**
The script `sys.exit`s on the missing input, so it is not runnable, only
unblockable.

The gap it closes: part of the `data/raw/external/state_gaming/` tree was
retrieved by reconnaissance agents whose URLs **live only in their transcripts**.
A raw tree whose provenance depends on a transcript is not reproducible — and
the transcripts may no longer exist, which is the same failure mode as §3's
dead-scratchpad finding. **Specified rather than half-built**, per the task: see
the queue entry.

**Blocked on:** a human, or a transcript archive.
**Effort:** manual transcription, recoverability unknown.
**The script's own rule governs it:** *`UNKNOWN` is a legitimate value and a
guess is not* — a plausible-looking wrong URL is worse than a blank, because it
will be believed and re-fetched and whatever comes back treated as the same
document.

### 7. `101_build_lodes_block_employment.py` — NEVER RUN, employment leg SUPERSEDED, **and the trap is now defused.**

**Value: low, and deliberately so — this entry is mostly a fix, not a task.**

- **Employment leg: SUPERSEDED** by `100_finish_declinations_and_employment.py`,
  which already shipped the LODES rows and keeps the raw `CNS17`/`CNS18` codes
  with a correct `measurement_note`.
  `docs/LABOR_SOURCES_FOR_GAMING_2026-08-26.md` (lines 405–425) says so and
  recommends *"fix it or delete it, but do not run it as it stands"*.
- **Geocode leg: NOT superseded.** `100` does not produce
  `facility_block_geocode.csv`, and `102_build_coverage_profile.py` still lists
  it as one of fourteen facility-hub sources. That leg is the only reason the
  file is still here.
- **The trap was fixed today.** See "What was fixed".

**Blocked on:** the Census Geocoder and LEHD host locks.
**Effort:** the geocode pass only. Do not re-derive the employment leg.

---

## 2. TRUE SIGNAL, no work owed by this script

**`102_build_coverage_profile.py`** — declares `gaming_employment_lodes.csv` and
`facility_block_geocode.csv` missing because they are `101`'s outputs, listed
among its fourteen hub sources. `102` ran today
(`logs/102_coverage_profile_2026-08-26.log`) and degrades gracefully on an
absent source. **Nothing is owed by `102`; the flag is a correct report of
`101`'s state** and it is left in place deliberately — suppressing it would hide
the dependency.

---

## 3. FALSE POSITIVE — all 45, by mechanism

Each mechanism is now blocked at source in `code/160_ship_gap_report.py` and
names the scripts it was costing.

### (a) The file exists, in a directory the index did not walk — 9

`build_file_index()` walked `data`, `dist`, `docs`, `review`, `logs`,
`graveyard`, `web_claude` and the project root. It did **not** walk `code/` or
`Federal Spending/`.

| script | declared path | actually at |
|---|---|---|
| `111_build_advocacy_passthrough.py` | `raw_filings.jsonl` | `code/lobbying_pull/raw_filings.jsonl` |
| `180_build_lobbying_registrant_hub.py` | `raw_filings.jsonl` | same |
| `_agent_akvillagecorp_build.py` | `_agent_akvillagecorp_docs.json` | `code/_agent_akvillagecorp_docs.json` |
| `115_pull_assistance_archive.py` | `Assistance_PrimeTransactions_2023-04-09_H19M53S53_1.csv` | `Federal Spending/raw/` |
| `16_federal_funding_recon.py` | same | same |
| `16c_copy_funding_inputs.py` | same | same |
| `24_funding_merge.py` | same | same |
| `227_anomaly_sweep.py` | same | same |
| `43_funding_forward_fill.py` | same | same |

### (b) An EXTERNAL input, outside this repo, verified present — 2

- **`01_build_entity_spine.py`** — all four paths exist under
  `Desktop/dissertation/data/tribal_federal_spending/` (`sam_extracts/` ×3,
  `clean/` ×1), checked individually. *(`01` remains FORBIDDEN TO RUN for the
  unrelated reason that a full rebuild drops every appended entity.)*
- **`156_stage_form5500_gaming_employment.py`** —
  `Desktop/4wheeler/casino_employment_validation/data/resolved_form5500_tribal.csv`
  exists, and `gaming_employment_form5500_staged.csv` exists, so it was read.

### (c) A space-split fragment of a real filename — 7

The tokeniser starts a name after the last space, so a filename containing
spaces was reported as its own tail while the file sat in `data/raw/`.

- `idvs.csv` ← **`Data Request 5-8-2023 IDVs.csv`**
  (`data/raw/esm_hci/ESM/raw/`) — `13_build_fpds_hierarchy.py`,
  `123_census_esm_raw.py`, `197_measure_pre2007_identifier_surface.py`,
  `198_compare_fpds_extracts_vs_prime_clean.py`,
  `201_value_of_pre2007_fpds_netnew.py`. **Five scripts, one space.**
- `dataset.xlsx` / `list.xlsx` ← **`Indian Gaming Dataset.xlsx`** and
  **`Tribal Property List.xlsx`** (`data/raw/external/gaming/directory_core/`) —
  `23c_copy_directory_core_sources.py`, `23d_build_gaming_facilities.py`.

### (d) A remote URL fragment — 4

- **`99_build_earmarks_and_schedc.py`** — the three House CPF spreadsheets
  (`06222021.csv_.xlsx`, `fy25-house-cpfs-as-requested-06.28.2024.xlsx`,
  `fy26-house-cpf-consolidated.xlsx`) are each the **fourth adjacent literal of
  one long `https://appropriations.house.gov/...` URL**. Only the first literal
  in the chain starts with `http`.
- **`73_add_tcu_and_cdfi.py`** — `nafi-map-data_current.xlsx` is the tail of a
  `github.com/frb-mpls-cde/nafi-map/raw/...` URL. **Also OUTPUT RENAMED:** the
  file was downloaded and landed as
  `data/raw/external/tcu_cdfi/cicd_nafi_map_data_2026-08-06.xlsx`.
- **`119_build_digital_and_loyalty.py`** — six Michigan internet-gaming
  spreadsheets, all `MI_MEDIA + "/Internet-Gaming---2024.xlsx"` shaped: a URL
  path glued to a host variable.
- **`186_cicd_benchmark.py`** — `Data_Dictionary_Crosswalk.xlsx` inside a
  mid-sentence citation of `https://files.usaspending.gov/docs/...`, i.e. the
  DAIMS-DEC crosswalk that `START_HERE.md` §5 quotes verbatim.

### (e) A fragment of a name whose other half is a variable, an escape, or a second extension — 8

| script | reported | really |
|---|---|---|
| `166_register_entity_link_block_fragments.py` | `ncodebook_master.csv` | `print("\ncodebook_master.csv NOT written here…")` — the `\n` |
| `263_register_attribution_repair_fragment.py` | `ncodebook_master.csv` | same sentence, same `\n` |
| `183_register_lobbying_registrant_layer.py` | `notes.json` | `Path(fname).stem + ".notes.json"`; the real ones are in `dist/` |
| `301_source_freshness_probe.py` | `partial.json` | `OUT_FULL.stem + ".partial.json"` |
| `15d_terms_extract.py` | `_review.md` | `a.out + '_review.md'`; four exist in `data/interim/` |
| `110_build_harmonized_views.py` | `_columnmap.json` | the closing half of an f-string; ten exist in `data/clean/views/` |
| `285_build_table_schemas.py` | `cedar_press.sqlite` | `docs/schema/cedar_press.sqlite.sql` — the second extension |
| `62_no_regression_check.py` | `ship_gap_cache.json` | `docs/.ship_gap_cache.json` — this report's own cache. **The dot.** |

Both `166` and `263` say, *in the very sentence that was misread*, that they do
not write the file.

### (f) Prose, or an API endpoint quoted in a citation — 2

- **`27_build_dataset_manifests.py`** — `documents.json` from
  `"citation": "federalregister.gov API v1, documents.json. …"`.
- **`76_build_recognition_history.py`** — `documents.json`, the same Federal
  Register endpoint, in generated markdown.

### (g) A filename handed to a BROWSER — 3

`a.download = "cedar_rulings___DATE__.csv"` inside generated HTML.
**`08_build_review_page.py`**, **`128_build_review_page.py`**, and
**`90_build_review_page.py`** — the last being the report's only `NEVER_RUN`,
a verdict that rested entirely on a client-side save filename.

### (h) A suffix test or a usage placeholder — 2

- **`72_fix_brand_and_government_misattribution.py`** — `final.csv` from
  `fname.endswith("final.csv")`. A predicate, not a path.
- **`287_build_dependency_manifest.py`** — `table.csv` from
  `usage: --check <table.csv>`.

### (i) ABSENCE IS THE SUCCESS CONDITION — 4

The most dangerous class, because each one reads as a gap and is the opposite.

- **`14_build_bills_votes.py`** — `_bill_votes_tallies_tmp.csv` is written, then
  `tmp.unlink()`ed at the end of `main()`. **Its presence would mean the run
  died.**
- **`36_cull_entity_candidates.py`** — `entity_discovery_pool.csv` is
  `.unlink(missing_ok=True)`, under the comment *"Retire the pool file if an
  earlier run created one."*
- **`85_build_admin_region_crosswalk.py`** — `admin_region_missing_bia.csv` is
  written **only inside `if missing:`**. Its absence means every federally
  recognised entity has a reviewed BIA region — a **passing check reported as a
  missing output**.
- **`143_build_gaming_property_locations.py`** —
  `gaming_property_locations_NO_NETWORK_PREVIEW.csv` is the refusal branch,
  written only when a `--no-network` run would otherwise overwrite a geocoded
  file. Absence means no offline run has had to be refused. *(Its other reported
  path, `dataset.xlsx`, is case (c).)*

### (j) Ephemeral by design — 2

- **`321_gate_tribal_source_restriction.py`** — `selftest.csv` is a fixture
  written into a `TemporaryDirectory` by `--selftest`.
- **`214_recover_nm_tribal_revenue_sharing_2023_2025.py`** —
  `_HOSTLOCK_klvg4oyd4j.execute-api.us-west-2.amazonaws.com.json` is a **host
  lock**. It exists *while* the pull runs; its absence is the released state.

### (k) A name in an EXCLUSION set — 1

**`173_consolidate_rulings_ledger.py`** — `cedar_ruling_application_log.csv` is a
member of `SELF_OUTPUTS`, listed so the ruling sweep never re-reads it and lets
a verdict double or a conflict become evidence for itself. **`173` never writes
it; `174` does.** The detector read a do-not-read list as a to-do list.

### (l) An optional input, guarded by `.exists()` — 1, and it hides a real defect

**`36_build_nho_intertribal.py`** — `doi_ein_results.json` /
`doi_ein_results_v2.json` are guarded salvage inputs, so the script runs without
them. **ABANDONED BY DESIGN as a declaration — but the guard hides something
that should not be filed and forgotten**, and it is queued separately in §5:

```python
SCRATCH = Path(r"C:\Users\esm247\AppData\Local\Temp\claude\C--Users-esm247-Desktop"
               r"\ea2ef30b-afc5-4319-b753-2cd3cb0d0ebb\scratchpad")
```

That is **another Claude session's temp directory**, and the session is gone. The
v2 file recovered **8 EINs (47 → 55)** with a diacritic-aware normaliser. Those
eight are **not reproducible**: re-running `36` today silently yields the 47-EIN
version and prints nothing about it, because the read is guarded.

### (m) ABANDONED BY DESIGN, verified against the code — 2 legs of `83`

**`83_build_resource_ledger.py`** — `cedar_transcribed_payments.csv` and
`cedar_transcribed_assets.csv`. The script's own comment:

> `# Optional supplement, not a gap. ND, UT and MT are built by the dedicated
> parsers above; this hook exists so a hand-transcribed series can be folded in
> later without touching the script.`

**Checked against this project's history of reversing "documented dead ends".**
`START_HERE.md` reversed tribal Single Audits after one auditee's opt-out was
generalised into a rule about the source, and `resource_assets.csv` went the same
way. **This is not that shape.** It is not a claim that the data cannot be got —
it is an *optional hook* that writes headers only and says so, and the sibling
`cedar_transcribed_cy_1996_2000.csv` **exists**, which proves the hook works when
a transcription is supplied. No reversal warranted. *(`83`'s third path,
`cedar_navajo_audited_actuals.csv`, is a real gap — §1.4.)*

---

## 4. What was fixed

### `code/160_ship_gap_report.py` — the extractor and the index

Backup: `code/160_ship_gap_report.py.bak_2026-08-26_pre_407_unfinished_work_audit`.
Written `.part`-then-renamed, AST-verified, and the report re-run four times to
measure each guard.

1. **`build_file_index()` now walks `code/` and `Federal Spending/`.** Nine false
   positives came from that omission alone.
2. **A URL chain is followed across every adjacent literal**, not just one
   predecessor — a long URL is four literals and only the first starts with
   `http`. Plus: a literal starting `/` is a URL path fragment, and an embedded
   mid-sentence `https?://\S*` is stripped before tokenising.
3. **A concatenation tail is a suffix, not a name.** `x.stem + ".notes.json"` is
   the same defect run 2 fixed for f-strings and missed here because `+` is not
   `{`. `}` was also added to the brace guard.
4. **Escape sequences are flattened** before tokenising, so `"\ncodebook_master
   .csv"` stops declaring `ncodebook_master.csv`.
5. **`NOT_A_DECLARATION`** rejects lines carrying `.download=` / `a.href`,
   `.endswith(` / `.startswith(`, `.unlink(`, and `<placeholder.csv>`.
6. **A file the script DELETES is excluded**, file-scoped rather than line-scoped.
7. **Prose (≥6 spaces) requires a path separator before the token.** A script
   that really writes a file also names it in a path expression, which is not
   prose, so nothing true is lost.
8. **`_best_name()`** recovers the longest form the project actually holds —
   space-containing names, second extensions, leading dots — and **every longer
   form is existence-gated, with the bare token as fallback**. That ordering is
   the safety property: it can only turn a reported gap into a satisfied
   declaration, never the reverse, **so a mistake there cannot hide a real gap.**
   An earlier attempt added the segment *unconditionally* and prose like
   `"=== building funding_identifier_harvest.csv"` came straight back as a
   declared path — the exact run-1 failure the tokeniser was written to fix.
   That attempt was measured (52 → 77, worse) and reverted before it shipped.
9. **`BY_DESIGN_ABSENT`** — a registry of declared paths whose absence is
   correct, **each with the branch quoted**, for the two shapes no static rule
   can see: written-only-on-failure, and optional/external inputs. In the idiom
   of `293`'s dispositions. It carries `85`, `143`, `321`, `214`, `173`, `36`,
   `83`, `01`, `156`, `14` — and an explicit note that
   `cedar_navajo_audited_actuals.csv` is **not** in it.

**Result: `scripts_output_missing` 52 → 10, `scripts_never_run` 1 → 0.**

### `code/101_build_lodes_block_employment.py` — the loaded trap, defused

Backup:
`code/101_build_lodes_block_employment.py.bak_2026-08-26_pre_407_unfinished_work_audit`.
**The script was NOT run**, per the standing prohibition.

`CNS17` and `CNS18` were labelled **backwards**, and the reversal pointed the
wrong way for exactly the column the script exists to produce:

```python
"CNS17": "jobs_accommodation_food",      # NAICS 72     <- was
"CNS18": "jobs_arts_entertainment_rec",  # NAICS 71
```

LODES WAC segments are the twenty NAICS supersectors in order
(`CNS01`=11 … `CNS20`=92), so **`CNS17` is NAICS 71 and `CNS18` is NAICS 72**.
The dict's own other three entries already agreed with that ordering — `CNS07`
retail (44–45), `CNS12` professional (54), `CNS20` public administration (92) —
which is what pins it. **A casino is NAICS 713210, sector 71, i.e. `CNS17`**, so
the file would have shipped casino employment under the hotel name.

Confirmed empirically by `100_finish_declinations_and_employment.py`, which is
correct: Wetumpka block `010510308011030` reads `C000=723, CNS17=688` — 688 arts
and entertainment jobs, which is the casino.

Fixed, with the reasoning and the Wetumpka check beside it, plus a `STATUS`
banner recording that the employment leg is superseded by `100` and that the
geocode leg is not. Nothing was contaminated: the script has no log and neither
output has ever existed.

---

## 5. Handed to the queue rather than half-built

Two items are the `122_ocr_ordinance_scans.py` shape — *a step promised in prose
that was never written*. Both are **specified, not started**, because both need a
decision or an artefact this pass cannot supply.

**A. `_retriever_urls.csv` for `107b`.** Write
`data/raw/external/state_gaming/_retriever_urls.csv` with columns
`relative_path, source_url, fetched_date, note`, one row per file in the
state_gaming raw tree, transcribed from the reconnaissance agents' transcripts.
Then `py -3 code/107b_fill_source_urls.py`, which merges `source_url` into
`_SOURCE_MANIFEST.csv` and prints a coverage report. **`UNKNOWN` is a legitimate
value and a guess is not.** If the transcripts are gone, the honest output is a
file of `UNKNOWN`s plus a count, which is still better than an undeclared gap —
and it makes the irreproducibility *visible* instead of latent.

**B. Persist the DOI EIN probe, and repoint `36_build_nho_intertribal.py`.**
Re-run the diacritic-aware DOI/IRS EIN probe over
`nho_doi_notification_roster.csv`, write its results to
`data/raw/external/nho/doi_ein_results.json` **inside the repo**, and change
`SCRATCH` to that path. Today the script reads a dead session's temp directory,
so **8 of 55 NHO EINs vanish on any re-run and nothing says so.** The fix also
removes a second hardcoded absolute path from a build script.

---

## 6. What was run, and what was not

**Ran:** `code/160_ship_gap_report.py` (read-only by its own final line —
*"NOTHING ELSE WAS WRITTEN"*), `code/293_lint_bug_classes.py`, and
`code/62_no_regression_check.py`, each before and after.

**Ran nothing from the still-wanted set.** Every one is blocked, and forcing any
of them would have collided with a live writer. Live at dispatch and re-checked
by PID before each decision: `121_pull_subawards_api.py` (usaspending lock),
`317_cdx_tribal_vendor_hosts.py` (web.archive.org lock),
`367_courtlistener_party_name_probe.py`,
`327_migrate_class7_keys_to_digests.py`, `293_lint_bug_classes.py`.

**Never run, and not run here:** `01`, `09`, `41`, `88`, `119`, `101`.

### Gate state

| | before | after |
|---|---|---|
| `lint_class7` *(tracked, must not rise)* | **42** | **42** |
| `lint_bug_class_instances` | 151 | 152–154 (moving; live agents are writing) |
| `62_no_regression_check.py` | FAIL | FAIL |

**`62` failed before and after, on nothing this pass touched**, and was not added
to. Its failures are (a) the **FA-01** `ANRC-BRBYCO-00` / *Bristol Bay Area
Health Corporation* correction not yet propagated to every table carrying the
claim — the live lobbying-correction pass, scripts 350–358, named in `AGENTS.md`;
and (b) new `class2c` instances in `382_remine_property_site_corpus.py` and
`384_crawl_uncrawled_open_properties.py`, plus a `class6` in
`98_build_oira_and_hearings.py` and a `class1` in
`164_link_facility_hub_sources.py`. **`382` is already named with its owner (the
property-site crawling agent) in `AGENTS.md`**; `384` is that same agent's newer
script. Neither file edited by this pass — `160` and `101` — appears in any lint
finding. The baseline was **not** re-recorded.
