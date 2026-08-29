# STRANDED DATA — DISPOSITION

*Written 2026-08-26 by `code/399_inventory_stranded_data.py`,
`code/400_promote_stranded_hearing_appearances.py` and
`code/401_register_root_csv_parts.py`.*

**This document exists so the next session does not re-investigate these files.**
Every line below is a decision with the check that earns it. The checks are
**re-run on every invocation** of 399 — a verdict that stops being true stops
printing, and prints as `CHECK-FAILED` instead. A ruling that is not
re-derivable is a note.

    py -3 code/399_inventory_stranded_data.py          # re-derive all of it
    py -3 code/399_inventory_stranded_data.py --json   # machine-readable

Machine-readable output: `docs/stranded_data_inventory.json`.

---

## THE HEADLINE

`docs/SHIP_GAP_REPORT.json` reported **521,566 rows in `data/staging/` and
`data/interim/` "never promoted"**, plus **7,009 rows in 8 root CSVs "no
registry enumerates"**. Both counts are **true as inventories and misleading as
gaps**, because both are computed from **where a file SITS** and never from
whether its **CONTENT landed**.

> **A STRANDING AND A DUPLICATE LOOK IDENTICAL FROM THE OUTSIDE.**
> The only thing that separates them is a membership check against the promoted
> table **on a real key**.

| disposition | files | rows |
|---|---:|---:|
| INTERMEDIATE-BY-DESIGN | 19 | 455,587 |
| ALREADY-LANDED | 19 | 71,394 |
| LIVE-WRITER (another agent, in flight) | 9 | 1,235 |
| SUPERSEDED | 5 | 1,234 |
| NEEDS-A-RULING | 1 | 326 |
| **PROMOTED** | — | **7** |

**Seven rows were genuinely stranded.** They are in
`data/clean/hearing_appearances.csv` now. The other 529,443 were already landed,
already ruled on, or are intermediates a later stage reads — and **each one is
recorded here as a decision so it stops being counted as a gap.**

---

## PROMOTED — 7 rows

`code/400_promote_stranded_hearing_appearances.py --apply`
`data/clean/hearing_appearances.csv` **2,667 → 2,674 rows, +2 columns.**

| id | witness organisation | congress | date | → entity |
|---|---|---|---|---|
| `CHRG-CHRG-111shrg53369-00` | Papa Ola Lokahi | 111 | 2009-11-05 | `NHO-PPLLKH-00` |
| `CHRG-CHRG-111shrg53064-02` | Papa Ola Lokahi | 111 | 2010-01-07 | `NHO-PPLLKH-00` |
| `CHRG-CHRG-112shrg67288-02` | Kamehameha Schools | 112 | 2011-05-26 | `NHO-KMHMHS-00` |
| `CHRG-CHRG-117shrg45086-00` | Papa Ola Lokahi | 117 | 2021-04-14 | `NHO-PPLLKH-00` |
| `CHRG-CHRG-117shrg48137-01` | Papa Ola LoKahi | 117 | 2022-06-01 | `NHO-PPLLKH-00` |
| `CHRG-CHRG-117shrg48137-11` | Kamehameha Schools | 117 | 2022-06-01 | `NHO-KMHMHS-00` |
| `CHRG-CHRG-119shrg60911-02` | Papa Ola Lokahi | — | 2025-05-14 | `NHO-PPLLKH-00` |

**Why they were stranded.** `98_build_oira_and_hearings.py` computes the Native
slice **against the spine as it stands on the day it runs.** It last ran
2026-08-07 with ~952 spine entities; the spine now holds 1,534 and the NHO layer
landed afterwards. All seven carry `resolution_basis = no_spine_match` — **not a
refusal, an absence**: the entity did not exist yet. Re-running 98 needs a
universe-wide network sweep, so 400 lands them instead and becomes a no-op once
98 runs again.

**How each was made safe**

- exact normalised match to a spine **canonical name** (not an alias, not a
  containment), verified against `data/spine/cedar_entity_spine.csv`
- passed through `code/cedar_match_guard.py`, whose 11 refuse-cases are 11
  defects that reached production; its self-test passes
- **tier INHERITED, never assigned** — 400 reads the `(tier, confidence)` that
  98 itself assigns to `resolution_basis = exact_name_only` **out of the live
  published table** (`B` / `0.90`, from 603 rows) and mirrors it. If the
  published table ever disagreed with itself, 400 refuses to run rather than
  choose.
- deduped on `hearing_appearance_id` — a deterministic id 98 mints from the CHRG
  package id, never a rank or a process hash
- **never blanks an existing `entity_id`**; it only fills blanks
- backup `hearing_appearances.csv.bak_2026-08-26_pre_400_promote_stranded_hearing_appearances`,
  `.part` then rename, re-read after the write (0 duplicate ids, 0 columns lost)

**IN-PLACE ENRICHER — ORDERING.** `98` FULL-REBUILDS this file and would revert
the promotion (defect class 6). The ordering is now written into `98`'s own
docstring under **RUN ORDER** and waived there with a reason. **If `98` is ever
re-run, run `400` after it.**

---

## NOT PROMOTED — and why. This list is the point of the document.

### 1. REFUSED: 76 rows that look exactly like the 7 above

`review/hearing_appearance_exact_name_refused_2026-08-26.csv` — every row names
the spine entity it would have matched and why it was refused.

83 corpus rows carry an exact normalised match to a current spine entity. Only 8
are `no_spine_match`. **The other 75 carry an explicit refusal the producer
already wrote down**, and the 76th is a publication-class question:

| corpus `resolution_basis` | n | examples |
|---|---:|---|
| `refused_specificity` | 34 | Fort Belknap Indian Community, NAFOA, NCAI, **`DC)`**, **`DC:`** |
| `refused_missing_native_identity_word` | 10 | Confederated Tribes of the Umatilla Indian Reservation |
| `refused_single_token_uncorroborated` | 10 | **Circle, Georgetown, Enterprise, "Hamilton"**, FirstBank, Hopi |
| `ambiguous_core:2_spine_entities` | 7 | King Island Native Community, Shoshone-Bannock |
| `refused_containment_uncorroborated` | 7 | Office of Hawaiian Affairs |
| `refused_state_disagreement` | 6 | Lumbee Tribe of NC, Legacy Bank, Pinnacle Bank |
| `ambiguous_containment:3` | 1 | Native Hawaiian Education Council |
| `no_spine_match`, individually Native-owned class | 1 | Tribal Energy Alternatives |

> **A REFUSAL IS A RULING, AND `entity_id == ""` DOES NOT SAY WHICH.**
> Reading a blank link as "unresolved" and re-matching it is **DEFECT 3** in a
> new coat — the same shape as `148` reading a RULED method as a POSITIVE
> ruling and publishing 317 owner exclusions as confident attributions.

`Circle`, `Georgetown`, `Enterprise` and `Hamilton` are Alaska Native village
names **that are also ordinary English words** — the identical defect `262` paid
for with `Eagle` three hours earlier the same day. `FirstBank` is a CDFI name
that is also a bank. **`DC)` and `DC:` are fragments of a postal address.**

The last row is different and is **NEEDS-A-RULING, not a refusal**:
`Tribal Energy Alternatives` is an exact canonical match to `CEDAR-ENT-000089`,
whose `entity_class` is **`Individually Native-owned business`**.
`cedar_domain.may_publish_individual_native_field` **fails closed** on that class
without an explicit consent ruling — *"a firm's own website statement is our
EVIDENCE, never their PERMISSION"* — so 400 does not make one.

### 2. ALREADY-LANDED — 19 files, 71,394 rows. Proved, not assumed.

**Promoting any of these inflates a published count.**

| file | rows | proof |
|---|---:|---|
| `staging/subawards_usaspending_2026-08-05/subawards_native_linked_2026-08-05.csv` | 53,417 | **0 uncovered** in `subawards.csv` on `(subaward_number, prime_award_unique_key, subaward_amount)` |
| `staging/subawards_raw_match/subawards_raw_match_2026-08-07.csv` | 8,513 | **0 uncovered**, same key. 55,035 + 8,513 = **63,548 exactly** |
| `contract-03-18-23-19-40-24.csv` | 4,000 | named in `13_build_fpds_hierarchy.py`'s `FILES`; cited by `source_file` on 28 rows of `fpds_uei_cage_map.csv` and 27 of `fpds_uei_edges.csv` |
| `staging/gaming_employment_form5500_staged.csv` | 2,046 | 1,975 present on `(ack_id, year, ein, employment)`; **the 71 absent are EXACTLY the 71 `262` withdrew as NOT_NATIVE** |
| `bgov.csv` | 878 | **878 of 878 CAGE codes** in `cedar_identifier_ledger_final.csv`, tier A, `bgov_manual` |
| `entity_master.csv` | 815 | 751 `Entity_ID`s on the spine's `cedar_entity_id`; 28 more match a canonical name or alias exactly |
| `entity_crosswalk_bgov.csv` | 752 | 878 of 878 CAGE codes in the ledger; named in `03`'s `AUTHORITY_FILES` |
| `staging/gaming_employment_osha_tribe_staged.csv` | 502 | **0 uncovered** on `(establishment_id, year, employment)` |
| `interim/ocr_shards/*.csv` (8) | 233 | **0 uncovered** in `gaming_ordinance_ocr.csv` on `(ordinance_id, pdf_md5)` |
| `Assistance_56G180126_TransactionHistory_1.csv` | 92 | **92 of 92** in `federal_funding_transactions.csv` on `assistance_transaction_unique_key`. A single-FAIN QA drill-down |
| `deals_2026_ytd.csv` / `deals_historical_2020_2025.csv` | 146 | merged by `153` on 2026-08-26; already declared parts |

> **THE `bgov.csv` TRAP, WRITTEN DOWN BECAUSE IT CAUGHT ME.**
> The identifier ledger stores the value in **`identifier`**, not in a
> `cage_code` column. A membership check aimed at `cage_code` returns **0 of
> 878** and reads as a total stranding. That is **defect 2b** — an absent column
> name reads as an empty source — and it produced one wrong conclusion in this
> session before being caught. `399` now raises on a missing key column instead
> of returning "nothing matched".

> **THE FORM 5500 TRAP.** The 71 rows absent from the promoted table are not
> missing. They are `Eagle` (an Alaska Native village name) capturing five
> Colorado/California/Washington/Kansas casinos, `Delaware Nation` capturing a
> Delaware **state** racino, `Native Hawaiian Community` capturing a card room
> in Hawaiian Gardens, **California**, and a BIE school captured by a casino.
> **Re-promoting them republishes a Delaware racino's Form 5500 as tribal.**

### 3. INTERMEDIATE-BY-DESIGN — 19 files, 455,587 rows. **87% of the "gap".**

These exist so a later stage can read them. **They are not gaps and must stop
being counted as such.**

#### The OIRA / hearings corpora — 189,111 rows

`interim/oira_meeting_participants_corpus.csv` (95,529),
`hearing_appearances_corpus.csv` (70,380),
`oira_federal_action_links_corpus.csv` (14,975),
`oira_meetings_corpus.csv` (8,227).

`98_build_oira_and_hearings.py` states the design **in its own source**:

> *"THE PUBLISHED FILE IS THE NATIVE SLICE. THE CORPUS IS CONTEXT. … Both sweeps
> are deliberately universe-wide … because there is no way to find the Native
> slice without reading the corpus. But the corpus must not be published AS the
> dataset. '2,146 OIRA meetings' in a Native product reads as 2,146 Native
> meetings, and on the 2014–2018 window that number is six."*

Verified: **every published slice row is present in its corpus (0 absent)**, and
**0 corpus rows qualify under 98's own slice rule and are missing from the
slice.** Publishing the corpus would ship ~187,000 non-Native rows as a Native
product.

#### `subaward_uei_netnew_2026-08-05.csv` — 252,078 rows. **Still not subawards.**

252,078 rows, **252,078 distinct `uei`**, **8 columns** — one row per UEI. A
**DIMENSION** table over the universe-wide pull. Summing it into a subaward row
count produces the phantom ~317k figure that fooled a previous reader. Only
2,308 of its UEIs are in the identifier ledger at all.

#### Compacts — 6,322 rows

`compact_authorizations.csv` (747) → **684 published by `92` into
`gaming_capacity_official.csv`**; the 63 absent are 60 `statewide_pool_or_tier`
rows routed to the review queue (they describe the STATE's licence pool, not a
tribe's ceiling) and 3 rows with **neither a tribe nor a state** — both refusals
written into `92`'s source with their reasons. `91`'s docstring is explicit:
*"Nothing is written to data/clean by this script. 92 assembles the published
file."*

`compact_authorizations_candidates.csv` (2,356) is every candidate **kept or
rejected**, with `kept` and `reject_reason`.
`terms_candidates_full.csv` (1,885) → 1,311 rows of `compact_terms.csv`; of the
574 not published, **545 are exactly the duration term types `15e` routes to
`compact_duration_candidates.csv`** (545 rows) because they feed
`compacts.term_end` / `renewal_provisions` and are not `compact_terms`
term_types; the rest are dropped for an ambiguous `source_pdf → version_id` join,
where `15e` refuses to guess.
`compacts_pdf_inventory.csv` (1,187) is a file inventory of the PDF corpus.

#### Deliberately withheld — `103_sdf_local_mitigation_unverified.csv`, 1,292 rows

Withheld **on the record** by `103`, for two reasons either of which suffices:

1. **No tribe is named.** The appendices are county → local agency → project →
   amount. Attaching a Riverside County fire-district grant to a tribe would be
   an inference from geography alone.
2. **The line items do not foot** against the printed per-county totals.

Promoting it publishes 1,292 unfooted dollar rows attributed by geography.

#### Build diagnostics and retrieval manifests — 6,466 rows

`103_zone_log.csv` (1,189), `105_zone_log.csv` (1,887) — PDF zone-parse logs.
`105_litigation_figures.csv` (48) — figures a party **asserted in a filing**;
an assertion is not a measurement and carries no tribe key.
`119_mi_footing.csv` (270) — an **arithmetic footing proof**
(`published`/`summed`/`foots`), not observations. **119 is on the do-not-run
list.**
`142_crawl_manifest.csv` (2,307), `142_gamefinder_manifest.csv` (223),
`142_property_domains.csv` (440) — HTTP retrieval manifests and the crawl's
**input frontier**; consumed by `142` and by `382_remine_property_site_corpus.py`.
`subaward_rows_by_fiscal_year.csv` (22) — a per-year count of a table that is
already promoted. Recompute it; never promote it.

### 4. SUPERSEDED — 5 files, 1,234 rows

`terms_pilot_candidates.csv` (429), `terms_candidates_v2/v3/v4.csv` (153/145/63)
— pilot iterations from `15c`/`15d` on **2026-08-05**, run over a **28-document
sample**, superseded the same day by `terms_candidates_full.csv` over the full
**1,187-document** corpus. The pilot's `dispute_provision` pattern returned 266
hits on 28 documents against the final run's 118 on 1,187 — **the divergence is
the pattern being tightened between iterations, not lost data.**

`subaward_native_entities_2026-08-05.csv` (444) — a derived rollup. The clean
`subaward_entity_rollup.csv` holds **450** entities, rebuilt from the promoted
63,548-row table. The 2 staged-only entities
(`AKNF-RAMPRT-00-DOYONL-CATHTG-TNNACH`, `TRBF-FMCDWL-00`) are excluded by the
rollup's **own declared `basis`** —
`duplicate_status==primary AND subaward_exceeds_prime_flag!=yes` — and both rows
carry `subaward_exceeds_prime_flag = yes`. Verified per row.

### 5. LIVE-WRITER — 9 files, 1,235 rows. **NOT RULED ON. HANDS OFF.**

Written inside a 90-minute window by agents still running at dispatch:
`data/staging/tribal_vendor_lists/*` (scripts 320–324, tribal certification),
`data/staging/gaming_property_*_2026-08-26.csv` and
`data/interim/384_property_domains.csv` (casino-site mining, scripts 382/384).

**399 classifies these by MTIME, not by a hardcoded name list**, because a name
list goes stale the moment the next agent picks a new filename — which is
exactly how `SHIP_GAP_REPORT.json`'s staging list drifted five files behind
reality between 20:28 and 21:00 the same evening. **Re-run 399 once those agents
are done.**

### 6. NEEDS-A-RULING — 326 rows

`reconcile_queue.csv` → **moved to `review/reconcile_queue.csv`** by `401`.

**326 rows, 326 with an empty `YOUR_RULING`.** It is not data; it is 326
unanswered questions: `neid_unmatched` 214, `village_corp_region_unmapped` 73,
`bgov_tribe_unmatched` 34, `deal_missing_source` 5. `160`'s `review_backlog()`
already globs `review/*.csv` and counts blank ruling columns, so it now lands in
a registry that **already exists and already reports by name**. Registering a
queue as a dataset part would have hidden it in the wrong list.

**Also needing a person:**

- **36 `entity_master.csv` rows match the spine by neither id nor name.** Ten are
  name variants with parentheticals that plainly are on the spine (*Native
  Village of Eyak (Cordova)*, *Te-Moak Tribe … (Four constituent bands: …)*).
  The other 26 are a curation question, not a promotion: `A-0008` Cook Inlet
  Region, `A-0010` Koniag, `A-0011` NANA, `E-0001` ASRC Federal, `E-0002` Akima,
  `E-0003` North Wind Group, `E-0005` Cherokee Nation Businesses, `E-0006`
  Chickasaw Nation Industries, `E-0007` Kituwah, `E-0011` San Manuel Investment
  Authority, `E-0018` Catawba Nation Gaming Authority, and 15 more. **Spine
  writes are governed by `01_build_entity_spine.py`, which is on the do-not-run
  list, and by append-merge only.**
- **`Tribal Energy Alternatives` → `CEDAR-ENT-000089`** — see §1.

---

## THE ROOT CSVs — registered, not folded

`cedar_domain.PROMOTED_TABLES` / `PROMOTED_TABLE_PRODUCERS` extended (appended,
so a concurrent editor of that module cannot lose the block):

| root file | declared part of |
|---|---|
| `entity_master.csv` | `data/spine/cedar_entity_spine.csv` |
| `entity_crosswalk_bgov.csv`, `bgov.csv` | `data/clean/cedar_identifier_ledger_final.csv` |
| `contract-03-18-23-19-40-24.csv` | `data/clean/fpds_uei_cage_map.csv` |
| `Assistance_56G180126_TransactionHistory_1.csv` | `data/clean/federal_funding_transactions.csv` |
| `deals_2026_ytd.csv`, `deals_historical_2020_2025.csv` | `data/clean/deals_classified.csv` *(already declared)* |

**All 7 remaining root CSVs now resolve through
`cedar_domain.promoted_table_for()`. `lint_class1` stayed at 0** — every reader
of a new part either reads the promoted table too or is named in
`PROMOTED_TABLE_PRODUCERS` with its reason (`01`, `03`, `13`, `35`, `36`, `52`,
`66`, `374`, `399`, `401`).

**They stay in the project root.** They are hand-built or hand-exported SOURCE
INPUTS that several builds name by literal path. Moving them breaks those builds
to tidy a directory listing — **the gap was never the location, it was that
nothing said what they were.**

> **`contract-03-18-23-19-40-24.csv` is EXACTLY 4,000 rows.** That is the
> USAspending Advanced Search download cap. It is a **truncated export** and must
> never be summed as a ledger. Only 1,857 of its 4,000 Award IDs appear in
> `prime_contracts.csv`, and that is a property of the export, not a gap in
> prime.

> **`bgov.csv` is PRE-AGGREGATED.** One row per contract-year-vendor with
> `i_sumofcontractstransactions`, against a transaction-level `prime_contracts`.
> 775 of its 878 `(contract, year)` pairs are already in prime. **Folding it in
> would double-count 775 rows and mix an aggregate schema into a transaction
> table.** Its value already landed — as 878 tier-A CAGE attributions in the
> identifier ledger.

---

## HANDOFF

**`160_ship_gap_report.py` still prints the root flat.** The one-line fix is to
call `cedar_domain.promoted_table_for(p.name)` in the `root_csv` loop (~line
1156) and print `DECLARED -> <table>` for a declared part, so section (g) reports
only what is genuinely unenumerated. **It was NOT applied**: `160` was being
edited by another agent during this run (`code/160_ship_gap_report.py` 20:51:49,
`docs/SHIP_GAP_REPORT.json` 20:53:36, both inside the live window). Concurrency
rule 6. Handed off by name rather than done over a live editor.

`code/401_register_root_csv_parts.py` already prints the disposition itself, so
the information is available today either way.

---

## GATES

**Run BEFORE any change**

| detector | state |
|---|---|
| `293_lint_bug_classes.py` | `class1=0` · `class6=33` · **`class7=42`** · total 151; **`class2c` rising 60→61 on `353_propagate_lobbying_corrections_to_consumers.py`** — the live lobbying-correction pass (350–358), named in `AGENTS.md` |
| `62_no_regression_check.py` | FAIL on 5 registry metrics — `ship_tables_at_zero` 138→139, `tables_missing_codebook_block` 139→140, `tables_missing_from_25_TABLES` 234→235, `tables_missing_from_27_SPEC` 249→250, `tables_missing_notes_contract` 139→140 — all one table, `cedar_correction_register.csv`, from `354_correction_register.py` (live) |

**Run AFTER**

| detector | state |
|---|---|
| `293_lint_bug_classes.py` | `class1=0` · `class6=33` unwaived-of-mine · **`class7=42` — UNCHANGED, the tracked gate metric did not move** · `class2c` back to its floor of 60 (that agent fixed it). One new instance: `class6` 33→34 on `entity_aliases.csv` |
| `62_no_regression_check.py` | FAIL on `lint_new_defect_instances=1`, `lint_class6` 33→34, `tables_missing_from_25_TABLES` 234→235, `tables_missing_from_27_SPEC` 249→250 |

**Every failing metric at handoff is another agent's, and each is named with its
owning script and its fix in `AGENTS.md`** under standing rule 15 response 3:

- `lint_new_defect_instances` / `lint_class6` → **`418_build_entity_alias_layer.py`**
  enriches `entity_aliases.csv` in place while
  `97_build_aliases_and_relationships.py` full-rebuilds it. Fix: write the
  ordering into `97`'s header and waive it there — **the waiver now works at
  line 1**, see below.
- `tables_missing_from_25_TABLES` / `_27_SPEC` →
  **`cedar_entity_identity_crosswalk.csv`** (10,107 rows), written by
  **`417_build_entity_identity_crosswalk.py`** at 21:02. Fix: register the
  codebook block, then re-run 87 → 25 → 27.

**Nothing this session added to the gate.** `class7` held at 42, `class1` held
at 0, and the one class-6 pair this session created
(`98` rebuilds `hearing_appearances.csv`, `400` enriches it) is answered: the
ordering is written into `98`'s docstring under **RUN ORDER** and waived there
with a reason.

### A detector bug found on the way, and fixed

`293`'s `detect_class6` reports at **line 1** (the finding is about the FILE),
and `apply_waivers` walked **upward** from the flagged line — starting at line 0
and stopping immediately. Line 1 is the shebang, so no waiver could be written
there either. **Every class-6 finding in the project was detectable and none was
answerable**, while the class-6 write-up in `AGENTS.md` explicitly asks that
"the ordering has to be written down by a person". For a line-1 finding only,
the module's leading comment block is now scanned downward. **Detection is
unchanged**; `--selftest` passes; waivers stay counted and named
(`WAIVED (17) — counted, named, not hidden`).
