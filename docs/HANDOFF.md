# HANDOFF — read this first, then START_HERE.md

*Written 2026-08-27 ~01:00. **This file goes stale fastest of anything here.**
Every number below was measured on 2026-08-26/27 with ~10 agents writing
concurrently. **Verify before you rely on one.** The durable rules live in
`AGENTS.md`; the durable dataset state lives in `START_HERE.md`. This file is
only "what was happening and what to do next."*

---

## THE ONE-PARAGRAPH VERSION

Cedar Press has ~7.4M shipped rows across 11 collections and the collection
work is largely done. **The bottleneck was never collection — it was the last
mile.** A session on 2026-08-26 found that 0.87% of publishable gaming rows
reached a shipping artefact, that six recurring code-defect classes each had
multiple undiscovered instances, and that several launch findings were
arithmetic or reporting artefacts. Most of that is now fixed or instrumented.
**The gate (`62`) and the linter (`293`) are the scoreboard — run them first.**

---

## RUN THESE THREE BEFORE YOU DO ANYTHING

```
py -3 code/62_no_regression_check.py      # the gate. A FAIL IS STOP-WORK.
py -3 code/293_lint_bug_classes.py        # 8 named defect classes, floors
py -3 code/160_ship_gap_report.py         # built-but-never-plumbed, ~2.5 min
```

`62` is load-bearing now. **"Pre-existing, not mine" is not a disposition** —
six sessions in a row stepped around one line and hid every other failure the
gate could have raised. If a failure is genuinely another agent's, name it and
its owner in `AGENTS.md` before continuing.

---

## 2026-08-28 EVENING — INFRASTRUCTURE PASS. GATE IS GREEN.

**`62` exits 0 with zero regressions.** It had been failing. Verify before
trusting anything below: `py -3 code/62_no_regression_check.py`.

Movement against the recorded baseline, all in the good direction:

| metric | was | now |
|---|---:|---:|
| `lint_bug_class_instances` | 182 | **147** |
| `lint_class6` | 33 | **30** |
| `lint_class7` | 74 | **42** |
| Type-A collisions (2+ wholesale writers) | 5 | **1** |

### One command per collection

```
py -3 code/build.py list                    # the 12 + the entity layer
py -3 code/build.py plan gaming             # ordered plan, rebuilds then enrichers
py -3 code/build.py run gaming --execute    # actually run it
py -3 code/build.py ship --execute          # the 7-step ship chain
```

**`ship` runs the chain `docs/SHIPPING_RUNBOOK.md` part 1 declares — all seven
steps, not the "87 → 25 → 27" shorthand** that appears in 62's failure text and
in several docs. That shorthand omits the codebook build, the gate, the coverage
profile and the harmonised views; shipping with a stale codebook is how gaming
shipped 912 of 104,412 rows.

Two guards on it, both of which had to be corrected once before they were right:

- **A lock FILE is not a held lock.** 534 `_HOSTLOCK_*.json` exist because the
  runner writes `active: false` on release rather than deleting. Refusing on the
  file count refuses forever.
- **`active: true` is not a held lock either.** Measured 2026-08-28,
  `_HOSTLOCK_eaglemountaincasino.com.json` read `active: true`, pid 10456,
  claimed 2026-08-27 — and the process was gone. WORK_QUEUE records the same
  shape blocking two queue items for **nineteen days**. So liveness decides:
  `ship` blocks only on a lock whose pid is alive, and names stale ones for
  cleanup. Current state: 534 files, 1 claiming active, **0 genuinely held**.

`build.py` holds **no knowledge of its own** — it reads `cedar_pipeline.NEVER_RUN`,
`all_orderings()`, 500's `COLLECTIONS` and 293's `class6_io_map`. Adding a
dataset is one entry in `500_build_architecture_map.py`, not an edit here.
Dry run is the default; `run` refuses without `--execute` and refuses outright
if any NEVER_RUN script is in scope.

### Ordering coverage went 5 → 80

`cedar_pipeline.KNOWN_ORDERINGS` had 5 curated pairs while 293 found 32 class6
tables, so 27 orderings existed only as a lint finding. `derived_orderings()`
now derives them from the detector itself; `all_orderings()` and
`enrichers_to_rerun()` are what a runner should call. **`cedar_entity_spine.csv`
had 1 declared enricher and actually has 15** — a rebuild silently reverts all
of them, which is why `01` is on NEVER_RUN.

### New generated docs — do not hand-edit, re-run the script

| doc | script |
|---|---|
| `docs/ARCHITECTURE.md` | `500_build_architecture_map.py` |
| `docs/ENTITY_INVENTORY.md` + `docs/entity_dataset_coverage.csv` | `501_build_entity_inventory.py` |
| `docs/ARCHIVE_CANDIDATES.md` | `502_archive_candidates.py` |
| `docs/IDENTIFIER_STANDARD.md` | **policy, hand-written** — carries no counts on purpose |

### Script discipline is now enforced, not advised

`code_duplicate_numbers` is ratcheted in `62` from a floor of **43**. A new
script reusing a taken number fails the gate. `ls code/<n>_*` before naming one.
`code_scripts_total` is tracked but not ratcheted — growth is legitimate,
collisions are not.

### Archived (moved, never deleted)

- `graveyard/2026-08-28_lobbying_v1_chain/` — the v1 pull/match/stats chain,
  superseded by 04/05/06. Both chains wrote the same three tables wholesale.
- `graveyard/2026-08-28_nho_disproven_8a_inference/` — `06_verify_nho_via_8a.py`,
  whose central inference 19's own docstring records as disproven.

Each folder has a `GRAVEYARD_INDEX.md` with the evidence and a restore command.

### WHAT TO DO NEXT, in order

1. **Document the 14 undocumented tables.** ~~`tables_missing_from_25_TABLES`
   is 234~~ — **that number is not the shipping gate and never was.**
   Measured 2026-08-28: `25_build_publication_layer.py` resolves its 37 curated
   overrides and then *everything the codebook documents* ("a new dataset ships
   by being documented", line 124). The real split is **199 shippable / 2
   licensed / 14 undocumented**. Two new gate metrics now say so:
   `tables_undocumented_in_codebook` (ratcheted, floor 14) and
   `tables_shippable_via_codebook`. The old 234 metric is kept — a curated
   override going missing is still worth knowing — but its failure text now
   says explicitly that it is not the gate.

   ~~So this item is **14 codebook blocks, not 234 registrations.**~~
   **DONE 2026-08-28: 14 → 3.** `tables_shippable_via_codebook` 199 → **210**,
   `codebook_variables` 4,502 → **4,600**. `392` now refuses nothing.

   Eleven codebooks written to `docs/codebooks/`, all definitions read off the
   data rather than composed: `00r_inflation_deflator`,
   `09g_fr_consultation_by_agency`, `04n_lobbying_target_entities`,
   `04p_lobbying_disclosure_verbosity_year`, `09h_agency_attention_vs_advocacy`
   (covers the year file too), `05n_tcu_roster`, `04s_lobbying_issue_family_year`,
   `05p_tcu_cdfi_ownership_evidence`, `17b_grantmaker_funding_overlap`,
   `07zi_gaming_mitigation_agreements`.

   **The three that remain are not mine to decide**, and `391` already ruled on
   two of them:

   - **`gaming_property_locations.csv`** — NEEDS_A_RULING. 741 of 2,212 rows are
     `publishable = N` and **no script applies that filter**. Writing a block
     would put all 2,212 rows in a notes contract and decide publication by
     default. *Question: who applies the filter — 143 at build time, or the
     bundler?*
   - **`consultation_agency_coverage.csv`** — NEEDS_A_RULING. A hybrid: half its
     columns are findings about agencies, half are counts of what we collected.
     *Question: split it, or ship it with the coverage columns tiered internal?*
   - **`wa_machine_transfers.csv`** — EMPTY, 0 rows across 18 columns. Either the
     build produced nothing or there are genuinely no transfers; nothing on disk
     says which.

   Two accuracy notes carried into the codebooks because the data demanded it:
   `grantmaker_funding_overlap` carries its own `row_caveat` (*a shared funder is
   not a shared position*) and `carries_institutional_position = 0` on every
   funder-activity row — the codebook leads with that. `gaming_mitigation_agreements`
   mixes `USD per year` and `percent of Net Win` in one `amount_value` column, so
   the codebook says never to sum it.
2. ~~**`prime_contracts_entity_year.csv`** — the last Type-A collision.~~
   **DONE 2026-08-28.** Not a v1/v2 pair: 40 builds the panel, 131 merges the
   631,507-row USAspending archive backfill and regenerates it. Running 40
   after 131 silently drops the backfill while printing a normal-looking row
   count. Declared `40 → 131`; the full chain for `prime_contracts.csv` is
   **40 → 131 → 207**.

   The structural collision still shows in 293 (131 does write the table
   wholesale) — a declared ordering documents intent, it does not remove the
   overlap. What changed is that **`build.py` now honours declarations**: a
   script declared as an `enricher` is placed in phase 2 even when it also
   rebuilds something, so 131 moved out of AMBIGUOUS and into phase 2.
   Before that fix, declaring an ordering changed nothing in the plan and the
   declarations were decoration.
3. **Two catalog collections have no dataset doc** — `native-owned-businesses`
   and `natural-resources`. `py -3 -c "...catalog_coverage()"` in
   `24_generate_dataset_docs.py` reports it. Do not fabricate the prose; the
   NEVER-do lists are the valuable part and have to be written by someone who
   knows.

3b. **Clean up the one stale host lock** —
   `logs/_HOSTLOCK_eaglemountaincasino.com.json`, `active: true` with a dead
   pid since 2026-08-27. It no longer blocks `ship` (liveness decides), but
   leaving `active: true` on a dead claim is what cost nineteen days once.

3c. **Verify `sam_extract_YkWOTVSRHn.zip`** — 52 KB against 48–50 MB siblings.
   Either a genuinely tiny Native Hawaiian slice or a truncated download.
   Cheap to check, and anything built on it inherits the answer.
4. ~~**NHO layer.**~~ **DIAGNOSED 2026-08-28 —
   `docs/NHO_LAYER_DIAGNOSIS_2026-08-28.md`.** Read it before touching this
   layer; the headline is that the 8 unpromoted register ids are **not 8
   organizations**:

   - **3 to mint** (Hoʻopale Foundation, Kalaimoku Foundation, Council for
     Native Hawaiian Advancement)
   - **2 duplicates** of entities already in the spine (`Hui Huliau Inc` →
     `NHO-HUIHUL-00`; `Office of Hawaiian Affairs - continued` →
     `NHO-FFCHWN-00`, a page-break artefact)
   - **2 natural persons** from a DOI notification list, plus one org whose
     line carries a person's name in a `c/o`

   **Promoting all 8 would put two named individuals into the entity spine as
   organizations.** Needs a ruling on whether a person who notified DOI belongs
   in an entity registry at all.

   Also: the register was **96% promoted** (210 of 218), not "never promoted" as
   an earlier note said. Coverage is **86 of 210**, having read 4 then 32 then
   86 as three separate reader bugs were fixed — never quote it without saying
   which tables were read. And four organizations worth **$587M** appear in the
   owner rulings and in neither the register nor the spine, which suggests the
   210 universe is materially incomplete.
5. ~~**The 55 archive candidates**~~ **DONE 2026-08-28: 55 → 5.**
   13 ANCSA scratch scripts archived to `graveyard/2026-08-28_ancsa_scratch/`
   (moved, indexed, restorable). Scripts 419 → **406**.

   **The detector was wrong twice before the list was usable, and both failures
   are the same shape:**

   - Round 1 flagged `ancsa_portal/lib.py`, which four sibling scripts
     `import` — `inbound_ref_count` matches filenames, not `import lib`.
   - Round 2 flagged **`04_pull_lda_v2.py`, the live lobbying puller** (whose v1
     had been archived hours earlier *because v2 is live*), plus `build.py`,
     `500`, `501`, `502` and `433_apply_elijah_recon_rulings_in_place.py`. A
     puller writes to `data/raw` not `data/clean`; a generator writes to `docs/`;
     nothing imports an entry point; none appear in a build plan — so they fail
     every structural signal while being entirely alive.

   502 now scores **seven** signals, including *named as a command in a doc* and
   *writes anywhere at all*. The five that remain are named in its output.

   **Left in place deliberately:** `55_stage_anc_subsidiary_rulings.py` — a
   proper 282-line script that staged an owner ruling batch. Retiring a ruling
   script is a decision about the audit trail, not code hygiene.

### 2026-08-28, LATE — THE ASSISTANCE TABLE IS ON CEDAR IDS. Owner-directed.

Elijah's directive: one identification system — ours. `503_reconcile_assistance_
to_cedar_ids.py` finished what the crosswalk started:

| `tribe_id_scheme_resolved` | before | after |
|---|---:|---:|
| `cedar_neid` | 26.2% | **78.3%** (final) |
| `lineageA_dofile_integer` (CICD) | 52.1% | **0.01%** — 44 rows: one researched EXCLUSION (Tuscarawas, an OH county agency) + stragglers |
| `unattributed` | 21.7% | 21.7% (untouched — no name to resolve) |

**361,307 rows moved across three passes. 359 of 361 legacy ids resolved —
100.0% of dollars, $107.50B.** The edge cases were finished by DOMAIN
KNOWLEDGE, now written down in `docs/NATIVE_ENTITY_NUANCES.md`: FR
parenthetical bands (Te-Moak x4, Paiute Utah x5, Capitan Grande x2,
Passamaquoddy x2), six renames, one tribally-owned enterprise attributed to
its ultimate owner, one non-Native exclusion, and Oneida decided by the
money itself (2,208/2,210 rows WI). Legacy integers preserved in `tribe_id` as provenance; backups at
`*.bak_2026-08-28_pre503`. **A rebuild by 24 reverts this — re-run
335 → 336 → 503 after** (ordering declared in KNOWN_ORDERINGS).

**Why this was allowed when 152/24 refused the crosswalk:** the ban is on the
CONTAINMENT MATCHER, not on reconciliation. 503 matches on exact normalized
name/alias, then distinctive tokens with three guards AGENTS.md itself
prescribes — government-class candidates only (which kills the Elim defect
structurally: the corporation is ANVC-class and can never be a candidate),
state agreement measured from the money's own `recipient_state_code`, and
leading-token/constituent rules. State words are never stripped, so Seminole
OK vs FL stays decidable.

**The residual, named:**
- **2 genuinely ambiguous** ($1.48B): ONEIDA NATION (NY vs WI both plausible)
  and SHOSHONE-BANNOCK (spine holds two CNSF constituents and no joint TRBF
  row — a spine modeling question, not a matching one).
- **24 spine gaps** ($1.28B): federally recognized tribes MISSING from the
  spine — San Manuel, Barona, Fort Sill Apache, Sokaogon Chippewa, Colusa,
  Northfork Rancheria, Pleasant Point, Aroostook Micmac and more. This is the
  minting queue, and it is now measured rather than suspected.

### UEI pass on the "unattributed" rows, 2026-08-28 (owner directive: a row
with a code is not unattributable)

89.5% of the 152,425 unattributed assistance rows carry a UEI; **63.5% of them
are already in our identifier ledger.** Applied with the tier discipline:

- **3,620 tier-A rows attributed** (scheme -> cedar_neid, basis names the UEI
  and method)
- **2,088 rows EXCLUDED** — their UEIs are owner-ruled tier X, NOT native.
  New scheme value `excluded_not_native`; attributing them would repeat the
  317-exclusions-published-as-attributions defect.
- **91,105 rows carry B/C proposals** in `tribe_id_neid_proposed(+_tier,_basis)`
  — the ruling queue for the nonprofit/entity push. Tier B never keys a dollar.

Final scheme split: **cedar_neid 78.8% · unattributed 20.9% ·
excluded_not_native 0.3% · lineageA 0.01%.**

**NEXT for the ID system, in order:**
1. **Historical-name alias backfill through 418's layer** — San Juan Pueblo ->
   Ohkay Owingeh (currently a live mis-match trap toward San Juan Southern
   Paiute), MHA / Mandan-Hidatsa-Arikara -> Three Affiliated, and the 503
   RESOLUTIONS set. An alias helps every matcher; a script dict helps one table.
2. **The 91,105 B/C proposals + np_orgs 12,366 UNRULED** — same work: name +
   address + IRS description against the spine. Address-vs-tribal-HQ matching
   is the owner-approved evidence channel for it.
3. **FERC linkage (1.08%)** with the 503 resolver + nuances knowledge.

### Open, needs a person

- **CICD crosswalk**: 361 mappings, $107.50B. Exact (27, $13.36B) and alias
  (46, $8.46B) are safe to promote; **containment (122, $36.56B) must not be** —
  AGENTS.md forbids containment from keying a dollar.
- **66 owner rulings** landed 2026-08-28 in
  `review/owner_rulings_cedar_recon_v1_2026-08-28*.{json,csv}` — 26 exclusions
  (tier X), 20 resolved, 20 needing a new entity. One held:
  `CENTRAL COUNCIL TLINGIT AND HAIDA` resolves to a compound id welding the
  tribe to Sealaska.
- **`casino_city_id`** in `gaming_facilities.csv` is the one proprietary id
  with no internal-only marking. Nothing ships it today.

---

## SESSION RESUMED 2026-08-28 — WORK RESTARTED

**The product repo is now cloned locally** at `C:\Users\esm247\Desktop\cedar-press-repo`
(branch `white-earth-ingest-and-encoding-fix`, pushed). It is a **PUBLIC** repo —
`teim-team/cedar-press`, verified by anonymous API call. **Nothing with named
individuals' personal contact detail goes in it.**

### The repo has a whole tribal business source registry we did not have before

`cedar_source_registry/` — 174 source programs, 583 of 584 nations checked
against the FR 2026-01-30 BIA list, 119 nations with source rows, 464 formal
negatives with recheck dates. Built by cloud sessions. Read its `CLAUDE.md` and
`HARMONIZED_SCHEMA.md` before touching it — the two-layer model is well designed
and easy to break (identity is an assertion array, never a boolean; conflicts
persist rather than overwrite; cross-reference sources can never originate an
ownership claim).

**Outreach waves 1 and 2 are already SENT** — 19 list requests from the owner's
Cornell address, replies expected ~2026-09-11. `cedar_source_registry/outreach/requests.md`
is the tracker. **Sending is human-only by standing rule; that file is the queue,
not the sender.**

### White Earth (TBD-113) converted Lead → Obtained

Owner supplied the 2026 certified-business register **and** the 2026 TERO
Ordinance on 2026-08-28. 22 layer-1 records, zero unparsed lines, 22/22
addresses. The ordinance gives us the **first quantified preference schedule in
the registry**: Chapter 6 categories C–F, plus a bid-price preference sliding
from **10% under $100k to 1.5% over $7M**, granted above the lowest responsible
bid.

⚠️ **The records are NOT in the repo and must not go in it.** They name 22
individuals with personal phone, email and home-address detail, and publication
rights are **unconfirmed**. They live at
`Cedar Press/data/restricted/white_earth_2026-08-28/`, referenced by the
registry row, blocked by `.gitignore`. **Possession is not a licence to publish.**
Provenance of the owner's copy is unrecorded — establish it before any
publication decision.

Two source defects recorded, not repaired: a phone with only 9 digits, and a
corrupted Chapter 6 category-C sentence (a numeric string is spliced into it,
destroying the level word). Category C's level is INFERRED from the surrounding
ladder — confirm against a clean ordinance copy before publishing the ladder.

### A cross-platform bug class was fixed in the repo — check for it HERE too

30 call sites plus one subprocess used the **locale** encoding: UTF-8 on the
Linux cloud runners, **cp1252 on this Windows machine**. Effects: the registry's
integrity checker reported 10 false join failures, and its append-only guard
could **never pass** on Windows (working file read as UTF-8, git baseline
decoded as cp1252). Three tools also *wrote* without an encoding, persisting
mojibake into the data.

**`subprocess.run(..., text=True)` decodes with the locale unless you pass
`encoding=`.** That one is easy to miss.

**A check that fails for an environmental reason trains people to ignore the
gate.** Ten permanent FAILs are indistinguishable from noise — this is the same
disease as the `62` line that six sessions stepped around.

Also fixed: `{k: c[k] for k in ORDER if c[k]}` silently dropped any status not
in a hardcoded list. **Vocabulary drift must surface as a new key, never as a
missing count.** Cedar Press local has the same pattern in places — worth a sweep.

### NEW TASK FROM THE OWNER — inbound list offers

The owner reports he has been emailing tribes and **some have replied saying
they will provide their list if contacted**. Those are conversions waiting to
happen and they are not yet in `outreach/requests.md`.

**Blocked on the owner naming which tribes replied** (or granting a look at the
replies). Do not guess and do not send anything — outreach is human-performed
by standing rule, and a wrong or duplicated ask damages a government
relationship that took real work to open.

### Agents dispatched 2026-08-28

Scrape wave A (Tulalip/Grand Ronde/Navajo/EBCI/Poarch) · scrape wave B
(CTUIR/Chickasaw/Choctaw×2/Muscogee/Cherokee/MN OSP) · FY2021 subaward
promotion · consolidation · SAM pull · apply-owner-rulings. Scrapers write to
`Cedar Press/data/staging/business_registry/` and **commit nothing** — a human
reviews before anything reaches the public repo.

---

## SESSION ENDED 2026-08-27 ~01:30 — CLEAN STOP

17 agents were stopped deliberately (owner running low on usage). **Zero stray
`.part` files** — the `.part`-then-rename discipline held under simultaneous
kills. State at stop: **spine 1,536 · ledger 20,577 · prime_contracts
1,217,768**.

### THE OVERNIGHT RUN FINISHED — FY2021 SUBAWARDS LANDED

Both armed scripts fired and both worked. Sequence, from
`logs/121_pull_subawards_api.log` and `logs/subaward_collect_retry.log`:

- **03:54Z — `fy2021` FINISHED: 765,109 rows, 231 cols, 172,118,201 bytes.**
  Server-side elapsed **23,613s (6h 34m)**. Checkpointed to
  `data/raw/subcontracts/usaspending_2026-08-12/All_Subawards_2026-08-26_H21M19S10550366.zip`.
- 03:57Z — submit deadline reached, host lock released cleanly.
- 05:35Z — the armed `collect` ran (correctly waited for the poller to die
  first), pulled `canary_2day`, and reported `still_outstanding=[]`.

**Zip verified 2026-08-27:** `testzip()` clean, two members —
`All_Contracts_Subawards_…csv` (467,834,058 bytes, **118 cols**) and
`All_Assistance_Subawards_…csv` (904,569,220 bytes, **113 cols**). 1.37 GB
uncompressed. **Not truncated:** raw newline count is ~1,300,757 against an
API-reported 765,109 rows, the expected direction for embedded newlines in
quoted description fields.

**✅ THE CSV-PARSED COUNT IS IN (2026-08-28), and it matches the API exactly:**

| member | cols | raw newlines | **true csv-parsed rows** |
|---|---|---|---|
| `All_Contracts_Subawards_…csv` | 118 | 294,132 | **242,337** |
| `All_Assistance_Subawards_…csv` | 113 | 1,006,627 | **522,772** |
| | | 1,300,759 | **765,109 — exact match** |

So the zip is complete, and the embedded-newline theory is confirmed rather
than assumed. **A bonus finding: the contracts member is 242,337 rows, which is
exactly the figure `rows_so_far` sat at for 390 minutes.** The counter was not
stalled and was not non-linear — it was reporting the FIRST MEMBER, complete,
while the second was still being generated. The "not monotonic-linear" reading
below was the right call for the wrong reason.

⚠️ **These are TWO UNIVERSES IN ONE ZIP.** Contracts and assistance subawards
have different column sets and different dollar bases. `RECONCILIATION_TOOL.md`
already forbids mixing them into one queue — **the same rule applies here. Do
not concatenate them.**

**Still outstanding — the hole is smaller but real.** Four server-side jobs
failed, all with the same opaque body `"An error occurred."`:
**`fy2022`, `fy2023`, `fy2024`, `fy2020_procurement`** (plus four older
diagnostics). So **FY2021 is closed; FY2022-24 is not.** Re-submit those in a
quiet window — and note the failure text carries no reason, so treat a repeat
failure as a signal to split the year, not to retry harder.

### THE MATCH GUARD REFUSED — and it was right, but it is drift, not corruption

`121 match` stopped at `"subawards.csv header is not the promoted schema"`.
**Diagnosed 2026-08-27, and the diagnosis is benign:**

`45_promote_subawards.COLS` declares **49 columns**; `data/clean/subawards.csv`
has **52**. All 49 are present **and in order**. The three extra are appended at
the end: **`subaward_amount_real2025`, `deflator_factor_2025`,
`inflation_base_year`** — written by a *later* inflation enricher.

This is exactly the concurrency rule in `AGENTS.md`: **the enricher runs after
the rebuild.** The guard compares the full list with `!=`, so a superset trips
it. **The guard did its job** — promoting 49-column rows into a 52-column file
would have silently blanked the deflator columns on every new row.

**The fix is an ordering decision, not a code fix — make it deliberately:**
either (a) promotion writes the 49 canonical columns and the inflation enricher
**re-runs after**, or (b) the deflator columns are promoted into `COLS` as
first-class and the enricher becomes idempotent. **(a) matches the existing
rule.** Do not "fix" this by loosening the guard to a prefix match and leaving
the extras unwritten — that is how the columns get silently blanked.

#### ✅ RESOLVED AND PROMOTED 2026-08-28. Read this before re-reading the above.

**FY2021 is promoted. `subawards.csv` 63,548 → 72,837 rows** (+9,289),
48,562 → 55,813 distinct identity keys, still 52 columns, coverage for
`subcontracts` finally off 63,548, **FY2021 173 → 9,462 rows**. $4.72B on 354
distinct entities, `duplicate_status=='primary'` and the exceeds-prime flag
both applied.

**But two things in the paragraphs above are WRONG, and they matter:**

**1. There is no separate inflation enricher. The enricher is `121 append`
itself.** Nothing else in `code/` writes those three columns to
`subawards.csv`. So "promote, then re-run the inflation enricher" is one
command, not two, and `121 append` both appends the staged rows and computes
the deflator for every row it writes.

**2. `41` → `45` CANNOT PROMOTE THIS PULL, and running `45` would have done
real damage.** Both read only
`data/raw/subcontracts/usaspending_subawards_2026-08-05`; the FY2021 zip is in
`usaspending_2026-08-12/`. Running `45` would have (a) not promoted FY2021 at
all, (b) re-read the live 63,548-row table through `load_existing()`, which
stamps `source_dataset=highergov_2023_export` on **every row it reads** —
written when that file held only the 998 HigherGov rows — and re-appended them
on top of a fresh rebuild of the same universe, and (c) written 49 columns,
reverting the deflator enrichment. **The route is `121 match` → `121 append`.**
`45` is now safe only for a from-scratch rebuild of the 08-05 corpus into an
absent or 998-row `subawards.csv`, which is not the state it is in.

**The guard fix, and why it is not the loosening warned against above.** The
old test was `header != m45.COLS` — strict equality. That deadlocked `121`
against **its own output**: `append` adds three columns, so from the first
successful append onward `match` could never run again. The corrected guard
requires **two** things, and a bare prefix test only checks the first:
the 49 canonical columns present and in order at the front, **and every column
beyond them one that `append` knows how to compute**. An extra column `append`
cannot fill still halts the run. The extras are **not** left unwritten:
**measured after the run, all 9,289 newly appended rows carry all three
deflator fields**, and the field-by-field verifier confirmed all 63,548
pre-existing rows byte-identical across all 52 columns.

**`append` is idempotent for the COLUMN ENRICHMENT but NOT for the ROW
APPEND** — confirmed by reading it, and this is the trap for the next agent.
`real()` is a pure function of `fiscal_year` and `subaward_amount`, so
re-running recomputes identical values and `adding` comes back `[]`. But
`append` does **not** dedupe against existing keys — `match` does that. So
running `append` twice with the staging file still present **appends the same
9,289 rows again**. Run it once, or move the staging file first.

**The two universes were NOT concatenated.** Contracts (6,484) and assistance
(2,805) are stamped in `award_kind` per row and never summed together, per
`RECONCILIATION_TOOL.md`.

### AN OPERATIONAL FACT WORTH KEEPING

`rows_so_far` sat at **242,337 for 390 straight minutes**, then jumped to
**765,109** and finished on the next poll. **The USAspending progress counter is
not monotonic-linear and a flat counter is not a stalled job.** Had this been
killed for looking hung — which is exactly what it looked like — the 6.5 hours
would have been lost. *(This is why it was left running through the stop.)*

~~**Next, supervised**: `41_match_subawards_to_ledger.py` →
`45_promote_subawards.py` → `35_coverage_audit.py` → `62_no_regression_check.py`.~~
**DONE 2026-08-28, but NOT by that sequence — that sequence is wrong and would
have damaged the table. See "RESOLVED AND PROMOTED" above.** What actually ran:
**`121 match` → `121 append` → `35_coverage_audit.py` → `62`.**

`code/retry_sam_downloads.ps1` also fired successfully — all six SAM extracts are
down. **DO NOT run `pull` — if in doubt, `collect`.**

### KILLED MID-FLIGHT — resume these, they were close

| work | where it got to |
|---|---|
| **Cedar ID system design** | was writing the design doc, the primary deliverable |
| **Per-dataset READMEs + lineage graph** | had the full picture, was writing the graph builder |
| **Consolidation (145 docs / 370 scripts)** | classification done, was building the detector entry point |
| **Bristol Bay repoint** | spine entities minted (1,536), was writing script 427 |
| **Apply the 33 owner rulings + FA-01** | analysis complete, was writing script 433 |
| **Dead guards / vocabulary drift** | was fixing the `cedar_match_guard` fixture |
| **API manuals + papers** (7 sub-agents) | **ONE LANDED AFTER THE STOP — see `docs/API_MANUALS_AND_QUIRKS.md`.** SAM/FAC/IRS/GovInfo/SEC, verbatim-sourced. Six remain unrun. |
| **RECAP ownership evidence** | *"a precise, court-supported ANCSA action item just fell out"* |
| **Casino site mining** | *"DNS failures are being read as blocks — need to separate NXDOMAIN from a refusal"* |

Their partial work is on disk and their briefs are in this conversation's
history. **Re-read `docs/WORK_QUEUE.md` and the relevant build log before
restarting one** — several had already written scripts.

---

## CORRECTIONS TO NUMBERS REPORTED EARLIER THIS SESSION

Recorded because the wrong versions circulated and may be quoted back:

- **"521,566 stranded rows" was 7.** The ship-gap detector counted *where a file
  sits*, not whether its content landed. 455,587 rows are intermediate by
  design, 71,394 already landed. **A file's location is not evidence about its
  content** — the detector still needs to measure membership, not position.
- **"52 unfinished scripts" was 8.** 45 of 53 were false positives — one
  "declared output" was a filename handed to a browser, and four were files
  whose *absence is the success condition*. Now `scripts_output_missing` = 10,
  `scripts_never_run` = 0.
- **`87`'s SHIP RATE printed 100.0% and it was a bug** — five values unpacked
  from an eight-value return, the `ValueError` swallowed, computing
  shipped-over-shipped. True figure **99.954%**. At one decimal the bug and the
  truth are the same string; the print is now three decimals.
- **"$14.98B in 8(a) families" double-counted** → $13.19B on 585 distinct UEIs,
  and they are tier-C *unattributed* — a question, not a finding.
- **"$1.92B Native-specific set-asides" mixes universes** → $1.2005B (0.49%) over
  attributed rows, $797.1M (0.45%) over tier A.
- **"36 rows" of over-stated `owned_by` tier was 2 live edges** (36 was ledger
  exposure).
- **The subaward FY2021-24 hole is upstream, not ours** — promotion closes
  exactly at 63,548 and every staged row was already landed.
  **↑ SUPERSEDED 2026-08-27.** Still true of everything that *was* staged, but
  **FY2021 has since landed as raw** (765,109 rows, on disk, unpromoted) and
  FY2022-24 failed server-side. So the hole is now: FY2021 = ours to promote,
  FY2022-24 = still upstream. See the overnight-run section above.
  **↑ SUPERSEDED AGAIN 2026-08-28 — FY2021 IS PROMOTED.** 63,548 → **72,837**
  rows; FY2021 173 → **9,462**. The remaining hole is **FY2022, FY2023, FY2024
  and FY2020-procurement only**, and all four are upstream server-side
  failures, not ours. Note what the promotion rate says about the rest: 765,109
  raw FY2021 subaward rows yielded 9,289 Native-linked rows (**1.21%**), so the
  three missing years are worth roughly 25-30k rows, not hundreds of thousands.

---

## WHAT WAS BEING WORKED ON (2026-08-26 into 27)

**Closed this session:** SAM FY2000-2007 (all six extracts, blocked 13 days) ·
FERC 307/307 dockets · NHOs 31 → 210 in the spine · the individual-Native class
created (45 rows, $2.34B off a discard pile) · deals 1 → 91 rows in 2026 ·
Federal Register and NAGPRA brought current · **$3.06B of per-tribe New Mexico
gaming revenue recovered from a "blocked" source that was a dead domain** ·
ship ratio 0.87% → 92.5%+ · class-7 positional keys 74 → 42.

**Still in flight at handoff** (check whether they landed): tribal certification
registry at scale · casino site/marketing mining · the Cedar ID system redesign ·
RECAP/CourtListener adjudication · the 139 unregistered tables · 521,566 stranded
rows · 52 unfinished scripts · Bristol Bay repoint · applying the owner's 33
rulings · taxonomy gap fixes.

---

## WHAT TO DO NEXT, RANKED

1. **Settle the launch headline. It has THREE values and none matches the file.**
   "Carries no Native set-aside" is recorded as 60.9%/$86.19B, 57.2%/$140.00B,
   and measures 59.75%/$146.24B. **The difference is entirely the award key** —
   `(contract_number, awardee_uei)` → $140.00B, `contract_number` alone →
   $129.82B, row-level → $146.24B. State the key and universe wherever it
   appears. The contractors launch piece leads on this.
2. **Reconcile the two identifier schemes in `federal_funding_transactions`.**
   365,535 rows on a legacy integer ($107.5B), 178,820 on an NEID. A per-entity
   total SPLITS an entity at the boundary; a distinct-entity count DOUBLE-COUNTS
   it. The crosswalk exists (344 of 361) but two scripts *deliberately* decline
   to apply it — **all 344 are tier B and 122 rest on the containment matcher
   AGENTS.md forbids from keying a dollar.** Honour that refusal.
3. **Run the shipping chain in a quiet window**: `cedar_codebook.py build` → 62 →
   87 → 102 → 110 → 25 → 27. Several downstream rebuilds are one refresh behind
   their parents (`fr_content_classification`, Section 106, recognition history,
   the OIRA join, FERC seeds, FOIA index), and **`169_build_identifier_graph.py`
   is stale from 17:57** with 3,883 attributions moved under it.
4. **The org role request (10/day → 1,000/day)** still gates SAM entity-management
   (the only exact EIN↔UEI route) and subawards FY2021-24.
5. **Three defects the API sweep found in code we already run** — all in
   `docs/API_MANUALS_AND_QUIRKS.md`, all cheap:
   **(a)** FAC truncates at exactly 20,000 rows **and returns HTTP 200** —
   `federal_awards` is ~2.5M, so any status-code-only check has been ingesting a
   slice. **(b)** FAC's own documented pagination example (`limit=4999`,
   `offset=5000`) **loses row 4999 of every 5,000**; if we copied it, we have a
   silent 0.02% hole. **(c)** `awardeeBusinessTypeName=INDIAN` matches unanchored
   and sweeps in `"Subcontinent Asian (Asian-Indian) American Owned"` — a South
   Asian ethnicity code. Grep for all three.
6. Then: the reconciliation queue (400 clusters, $35.81B), and the editorial
   slate in `docs/EDITORIAL_PIPELINE.md`.

---

## OPEN DECISIONS — THE OWNER'S, NOT YOURS

| item | at stake |
|---|---|
| 7 firms ruled `NATIVE` with no owner named | $2.75B — one sentence each |
| 2,289 new individual-Native candidates | $6.83B, 51x the class, all tier C |
| 49,792 rows classed ENTITY_OWNED **by substring alone** | $4.45B |
| 444 gaming open-date re-sourcings · 43 NIGC duplicates | — |
| Whether `deals` stays typed as deals | 623 of 935 rows are grants, not acquisitions |

---

## RULES EARNED THIS SESSION (the full set is in AGENTS.md)

- **Built is not done. Shipped is done.** Every build log confesses defects; not
  one asked whether the table could leave the building.
- **A ruling not applied back to its source table is not a ruling, it is a note.**
- **A RULED method is not automatically a POSITIVE ruling.** `148` published 317
  tier-X exclusions as tier-A attributions on that mistake.
  **`status` says a ruling was processed; `outcome` says what it decided.**
- **Our own defect, published as a fact about the source** — a column name that
  does not exist read as 0% coverage for 19 days; a `setdefault` no-op blanked
  10,661 tiers that a later agent reported as "the source records no tier."
- **A guard that exists but is never called is worse than no guard.** The ANCSA
  class guard has zero importers; the ruling was enforced by one script's local
  copy. Four more guards filter on strings that are not in the spine.
- **A test that passes for the wrong reason.** FA-02's detector scored 94 on the
  `georgt` substring of an entity id, so it would have read clean the moment the
  id was blanked even if the bad link returned.
- **A key that is positional or `hash()`-derived is an artefact of one run.**
  `ferc_filing_id` kept 4 of 2,534 ids across builds; a rank join briefly gave
  one firm another's ownership sentence.
- **A dead wrapper is not a dead poller.** nohup → py → python; the harness
  reports the shell.
- **An API's floor is a fact about the API** — FAC's API starts 2016; its bulk
  archive reaches FY1998.
- **A 403 is a fact about ONE ROUTE, not the document.** `nmgcb.org` was a
  lapsed domain re-registered as a casino affiliate site; the regulator was at
  `gcb.nm.gov` all along.
- **Wayback is not a route around a login.**
- **A tier is INHERITED from the source row, never assigned by the consumer.**
- **A name is not a key.** Never accept a ruling export without an identifier.
- **A corporate family stem is not a firm identity** — `{asrc, federal}` matched
  18 distinct subsidiaries.
- **Marketing copy is promotional, not audited.** Capture the verbatim sentence.
- **A digest of a UEI is reversible** by enumerating SAM's entity space — it is
  not a privacy control.

---

## THE HARD CONSTRAINTS

**NEVER RUN:** `01_build_entity_spine.py` (drops appended entities — the NHOs
were lost this way) · `09_import_rulings.py` · `41_build_codebooks.py` (would
delete 21 of 43 codebook blocks) · `88_build_deals_taxonomy.py` · `119_build_
digital_and_loyalty.py` · `101_build_lodes_block_employment.py` (CNS17/CNS18
swapped — would ship casinos under the hotel label).

**Licensing:** Casino City is QA-reference-only, never publishes — the gate now
runs at column definition, and 404,236 populated DUNS values once reached a
shipping artefact because a declared gate was never implemented. **D&B Open Data
is a THREE-WAY cutover, not one date** — registrations by *last-updated*,
exclusions by *created*, awards by *award date*, all 2022-04-04 (quoted verbatim
from `sam.gov/about/terms-of-use` in `docs/API_MANUALS_AND_QUIRKS.md`). Written
attribution to D&B is required and **bulk redistribution is prohibited**; our
constraint previously named the award leg only.

**Privacy:** Cedar Press names an individual only where a public professional
capacity is established, and does not publish datasets about private
individuals. Both are quoted from existing tables, not invented.

**Sovereignty:** tribal sources are governments' own publications. robots.txt
absolute; a directory behind a login is out of scope; `TRIBAL_SOURCE_RESTRICTED_
FILES` fails any build publishing without `OPT_IN`.

---

## WHERE THINGS ARE WRITTEN DOWN

`AGENTS.md` (durable rules, defect classes, concurrency) · `START_HERE.md`
(dataset state) · `docs/WORK_QUEUE.md` (the queue) · `docs/CEDAR_TAXONOMY.md` ·
`docs/ASSUMPTIONS_AND_LIMITATIONS.md` (reporting-regime confounders — read
before publishing any trend) · `docs/ANOMALY_REPORT.md` · `docs/SHIPPING_RUNBOOK.md`
· `docs/CEDAR_ID_SYSTEM.md` · `docs/RECONCILIATION_TOOL.md` ·
`docs/DOC_CONTRADICTIONS_2026-08-26.md` (**check this before trusting any doc**).

**Keep this file current.** If you finish something here, strike it and say what
replaced it. A stale handoff is worse than none, because it is believed.
