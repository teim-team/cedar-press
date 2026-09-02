# AGENTS.md — Native Deals & Native Entity Enterprise Data Project
*Operating guide for AI-agent sessions. Written 2026-07-31 from the full Q3 build conversation. Owner: Elijah Moreno.*

---

## HOW TO READ THIS FILE (added 2026-09-02)

**This file is ~6,000 lines and growing, and it is not an onboarding document.**
(Exact count: `wc -l AGENTS.md` — do not trust a figure typed here, including this
one.) Everything below
`CURRENT STATE (2026-08-06)` is an **append-only journal** — named gate failures,
defect post-mortems, and hard-won findings, written as they happened. That journal is
the most valuable thing in the repo and it should keep growing. It is also, read
linearly, roughly 90,000 tokens of context an agent spends before writing a line.

**Read this file in three parts:**

1. **The two sections immediately below** — the Prime Directive and
   `CURRENT STATE (2026-08-30)`. These are current and load-bearing. ~130 lines.
2. **`docs/AGENT_FIELD_GUIDE.md`** — ~200 lines. The traps distilled: why a green
   check here is often measuring something else, why four of five duplicate
   allegations were phantom, why `ls code/<n>_*` cannot stop a script-number
   collision, and which shared files destroy your work if you rewrite them.
3. **Then grep this file** for the dataset, script number or defect class you are
   actually touching. Do not read it front to back.

**And before you write anything:**

```
py -3 code/1050_preflight.py
```

It claims a script number **atomically** (`O_CREAT|O_EXCL` — the OS refuses the
second caller, which `ls` cannot), prints the shared files that need marker
discipline, reads `NEVER_RUN` **live** out of `cedar_pipeline.py` instead of from
prose that goes stale, and gives you `ondisk <term>` to check whether the thing you
are about to download is already on this machine. 27 of 39 ranked "missing" items
were already local.

> **Adding to the journal?** Keep doing it — this is how the repo teaches. Two asks:
> put the *rule* in the heading so a grep finds it, and if the finding is a trap the
> next agent will hit blind, add a row to `docs/AGENT_FIELD_GUIDE.md` too. Nothing in
> this file is ever deleted.

---

## What this project is
Three interlocking data assets, built to TEIM-grade evidentiary standards:
1. **Deal ledger** — `native_deals_quarterly_factcheck_2026Q3.xlsx`: `Deals_2026_YTD` (76 records) + `Deals_Historical` 2020–2025 (56 records), every row source-linked.
2. **Entity universe** — `Entity_Master` (815 rows: 588 BIA TLD entities, 12 ANRCs, 173 village/urban corps, 6 group corps, enterprises/subsidiaries, 7 NHOs) + `Entity_Crosswalk` (752 tribe→vendor DUNS/CAGE mappings from the BGOV file) + `FPDS_Entity_Extract` (UEI/CAGE incl. ultimate parent).
3. **Outcomes panel** — `Tribal_Obligations_Panel` (FY2000–2022, 230 lower-48 tribes, $25.5B nominal, QC-flagged).

## THE PRIME DIRECTIVE
**Zero fabrication.** Never write a deal row, dollar amount, date, or identifier that is not present in retrieved or uploaded evidence. When evidence lacks a date, skip the row and name it in the run log (see RUN-2026Q3-008: two skipped leads). A smaller true dataset always beats a larger padded one. When context runs low, stop adding rows and close out cleanly — degraded-context transcription is fabrication with extra steps.

## CURRENT STATE (2026-08-30) — THE MANDATE CHANGED. Read this before anything else.

*Everything below this section, including the 2026-08-06 CURRENT STATE, is history. It is
still true about what happened; it is no longer what you should optimise for.*

### The objective

**Not** "make Cedar architecturally sound." That phase produced real value and is
substantially done. The objective now is:

> **How many Cedar datasets can we confidently ship, update later without heroics, and
> expect customers to join and aggregate correctly?**

**Start every session at `docs/DATASET_READINESS.md`** (regenerate:
`py -3 code/518_dataset_readiness.py`). It reports **READY / BLOCKED / NOT_TESTED** per
dataset with named blockers.

**There is no fourth status.** Do not write "mostly ready", "substantially complete",
"green-ish", or "effectively done". A dataset crosses the ten-point production contract in
`518_dataset_readiness.py` or it has NAMED blockers. Vague statuses are how nine datasets
sit at 80% forever.

### The ten-point contract a dataset must cross

C1 validated grain · C2 validated primary and join keys · C3 duplicates removed or
explained · C4 central identity system, no silent resolution of dangerous ambiguity ·
C5 every harvested row has a NAMED disposition · C6 unresolved identity conflicts do not
ship as definite facts · C7 no known double-counting path · C8 ONE documented rebuild path
that does not destroy later enrichment · C9 an update procedure another session can execute
from the document alone · C10 regression and semantic-diff gates cover the outputs.

### How to choose work

1. **Customer-facing correctness defects first.** A wrong number a buyer will actually
   compute outranks any architectural improvement.
2. **Then close the dataset nearest the line.** Prefer turning *9 datasets at 80%* into
   *3 READY + 6 at 80%* over moving all nine to 85%.
3. **Architecture work needs a licence.** Do it only when it blocks a dataset from READY,
   prevents a demonstrated customer-facing error, removes repeated manual work across
   datasets, makes updates materially safer, or closes an adopted release requirement.
   Otherwise it is backlog. **Do not perfect a mechanism because a review found a
   theoretically possible edge case.**
4. **Fix the generating pipeline, never the output CSV.** Hand-cleaning a shipped file is
   a defect that returns on the next rebuild.

### Rules this arc paid for — violate these and the work is wrong

- **A check does not count until a fixture proves it FIRES.** Inject the violation, exit 1,
  restore, exit 0, and assert the NAMED invariant fired, not merely that the gate went red.
  A check that has never failed on purpose is not known to work.
- **A check reading a key that does not exist passes for the same reason it is useless.**
  This happened three times in two days: an export gate reading a duplicate-count field the
  probe never wrote; a scoreboard globbing release manifests at the wrong path; a resolver
  matching a literal that had just been deleted. **Verify your input actually contains what
  you think it does before trusting a green result.**
- **Authority belongs to a source's CLAIM, never to our match.** The Federal Register is
  authoritative about what its row says, not about which Cedar entity it refers to. Keep
  those separable and separately refutable — `docs/SOURCE_RECORD_LAYER.md`.
- **Modelling uncertainty is worthless if the export collapses it.** Unknown may ship as
  unknown. **Contradicted may never ship as definite.** `docs/EXPORT_SAFETY.md`.
- **Unknown stays unknown.** Never invent a date, an owner, or a boundary to make an
  interval tidy or a column deterministic. Deterministically wrong metadata is worse than
  deterministically missing metadata.
- **Every dropped row gets a NAMED reason.** `other` / `unknown` / `misc` are refused.
- **A falling metric is not automatically an improvement.** Deleting unsupported facts
  improves the same counter that adding provenance does. Track disposition, not just count.
- **Never re-baseline to clear a red gate.** `--baseline` records a floor while GREEN. A
  gate you stepped around is a gate the next six sessions will also step around.
- **Check `cedar_pipeline.NEVER_RUN` before any rebuild.** Several destroy later
  enrichment. Run `py -3 code/build.py plan <collection>` first, every time.
- **Self-verification is refused.** A completion claim is a row in `513_handoffs.py` with
  re-executable commands; a different session runs them. "I checked it" is not evidence.

### Parallel agents

When several agents run at once, file ownership is declared **before** editing in
`docs/ARCHITECTURE_DECISIONS.md`. No agent commits — an integrator verifies claims against
live data and commits. Only one agent may own a central file per pass. If two need
incompatible changes to the same file, stage them; do not race.

#### OPEN GATE FAILURE — RE-OPENED 2026-09-02 02:1x, measured by the staleness pass

**`py -3 code/62_no_regression_check.py` exits 1.** It exited 1 at 01:15 too, on
a shorter list; the list GREW during the pass because five other workstreams
were writing to `data/clean/` at the same time. Named, with the owner each line
points at, so nobody records this as "pre-existing, not mine":

| line | owner named by the evidence |
|---|---|
| `lint_class1 0 -> 1`, `class2c 60 -> 65`, `class3 0 -> 2`, `class4 9 -> 12`, `lint_new_defect_instances = 17` | the NEW scripts 293 names: `1011_cross_dataset_reconciliation`, `1060_splink_pilot`, `992_newsletter_deal_candidates`, `1030_sec_edgar_native_transactions`, `1031_ancsa_45_55_139_annual_reports`, `852_extend_constellation_edges`, `873_build_aiannh_crosswalk` |
| `class6`: `518_dataset_readiness`, `870_build_geo_crosswalks` | the readiness and geo-crosswalk workstreams |
| `tables_undocumented_in_codebook 3 -> 18`, `tables_missing_codebook_block 3 -> 18`, `tables_missing_notes_contract 14 -> 18`, `ship_tables_at_zero 13 -> 17`, `tables_missing_from_25/27` | the ~12 `geo_*`, `regulations_gov_*` and constellation tables created 2026-09-02. **A table without a codebook block cannot ship.** `cedar_codebook.write_fragment`, then 87 → 25 → 27 |
| `hearing_bill_links 465 -> 464`, `native_bills_subject_sweep 2,414 -> 2,409` STOPPED SHIPPING | the bills/votes workstream (`.bak_2026-09-02_pre890` on `bill_votes.csv`). Surfaced by an 87 re-run; the CAUSE is the tables shrinking, not the re-run |
| `rulings_unapplied 1,215 -> 2,894` | the rulings-consolidation workstream. 2,894 `CONFLICT_NOT_APPLIED` in `cedar_ruling_ledger_consolidated.csv` |
| `entity_evidence_profile.csv 10 -> 9 columns` (lost `in_spine`, `rows_per_source`, `amounts_per_source_NEVER_SUM`) | `505`. A rebuild reverted an in-place enricher; re-run the enricher |
| `contract_violations 7 -> 12`, `contract_orphan_shippable 6 -> 7` | the new-table owners above; `docs/schema/dataset_contracts.json` names each |
| `SHIPPING LOST: advocacy_passthrough_2026-08-07.csv` | pre-existing since 2026-09-01, unowned. The table is gone from `data/clean` and was shipping 1,620 rows |

**Two lines that WERE on this list on 2026-09-01 and are NOT any more** —
`files_with_columns_lost_vs_backup` fell 3 → 1 as the 843 backups aged out, and
`lint_class6` fell 29 → 24.

**Nothing here was waived and no baseline was re-recorded.** The staleness pass
owned two class7 instances of its own (`id()` used as a key in
`940_staleness_sweep.py`) and fixed them rather than adding a `# lint-ok`.

**The ship chain is therefore correctly blocked.** `289_update_collection.py`
stops at step 4 on a red 62, which is why `dist/collections/*.json` (2026-08-26),
`dist/manifests/*.json`, `dist/schema.sql` and `dist/cedar_press.db` still carry
`tribe_id_scheme` a day after 843 retired it. Those four cannot be legitimately
rebuilt until 62 is green. `dist/*/notes.json` WAS rebuilt (87 alone,
out of chain, deliberately) because it named a column that no longer exists.

#### ~~OPEN GATE FAILURE~~ — CLOSED 2026-09-01. `62` exits 0.

**Re-measured 2026-09-01 by workstream H: `py -3 code/62_no_regression_check.py`
exits 0 and prints `no regressions`.** The correction-register row was written,
the shipping allowance was repaired twice over (it compared dist-to-dist when
the metric sums `min(dist, clean)`, and `ship_ratio_pct` then failed on the
same fall the line above had just allowed), and the baseline was recorded while
green — `data/clean/_regression_baseline.json` now carries
`ship_dist_rows = 8,461,252`.

Also verified rather than assumed: `prime_contracts_entity_year.csv` is
**6,715 rows with 0 literal duplicate rows**, which is the collapsed grain the
correction declared. The regain of the 1,749 rows is neither owed nor wanted.

**The paragraph below is kept because the reasoning is the valuable part** —
this is what a correctly named, correctly owned gate failure looks like, and it
got fixed instead of inherited. It is history, not an open item.

##### The failure as it stood, 2026-08-29

`62_no_regression_check.py` exited 1 as of 2026-08-29 11:40 on:

```
!! ship_dist_rows FELL 8,463,001 -> 8,461,252
!! ship_ratio_pct FELL 99.774% -> 99.773% AND shipped rows fell too.
```

**Owner: the prime-contracts / contractors workstream.** Measured, not guessed:
the fall is **exactly** `prime_contracts_entity_year.csv`, shipped at 8,464 rows
in `dist/02*/…notes.json` and 6,715 rows live — a delta of **1,749**, which is
the whole of the regression to the row. The file was rewritten six minutes
before the gate run by the new, uncommitted `code/428_rebuild_prime_entity_year.py`
(`code/40_build_prime_contracts.py`, `code/131_merge_archive_backfill.py`,
`code/114_pull_prime_archive.py` and `code/cedar_prime_panel.py` are modified in
the same working tree). No other table in the shipping scan moved by an amount
that could account for it; every other recently-touched table GREW.

Nothing in the `federal-register` closure pass touches that table, that script
or `dist/`. `federal-register`'s own gate is
`py -3 code/519_closure_federal_register.py verify`, which exits 0, and the two
lint counters this pass did move went DOWN (`lint_class6` 30 → 29,
`lint_bug_class_instances` 147 → 146).

Whoever owns 428 either restores the 1,749 rows or declares them in
`cedar_correction_register.csv` with a `rows_removed` total EXACTLY equal to the
fall — 62 allows a decline only on that exact arithmetic, deliberately.

---

## CURRENT STATE (2026-08-06) — superseded by the section above, kept as history

Much of this file was written 2026-07-31 and describes an xlsx-centred project. **The build is now a script pipeline in `code/`, numbered in run order, writing to `data/clean/`.** Where a 07-31 statement conflicts with this section, this section wins. The older sections are retained because their *findings* remain true; their *counts and queues* do not.

- **Entity spine: 1,310 entities**, not 687. `data/spine/cedar_entity_spine.csv`. Classes now include `BIE School` (185), `Alaska Native Village Corporation` (173), `State-recognized tribe` (64), `Native CDFI` (64), `Intertribal Organization` (55), `Urban Indian Organization` (43), `Tribal College or University` (37), plus tribes and Alaska Native villages.
- **`code/33_apply_party_rulings.py` holds the ONE resolver.** Import `resolve_entity`; never write another name matcher.
- **`code/62_no_regression_check.py` is the gate, and as of 2026-08-26 it is LOAD-BEARING. See the section below before you step around a FAIL.** Fifteen standing rules in its docstring. Run it before declaring anything done.
- **`data/clean/series_breaks.csv`** (script 86) records every point where a source changed what it counts. **`dist/*/notes.json`** (script 87) is the per-dataset notes contract the app renders into the branded PDF. Presentation lives in the app repo; facts live here.
- **`docs/CROSS_SOURCE_VERIFICATION.md`** is standing policy: one federal source is a claim, two that agree is a verification, two that disagree is a finding.

### `09_import_rulings.py` IS ALSO UNSAFE TO RUN (confirmed again 2026-08-08)

This is already implied by standing rule 10 and it caught me anyway. **09
rebuilds `cedar_identifier_ledger_final.csv` FROM `cedar_identifier_ledger_tiered.csv`**,
and `_tiered` is stale — it does not carry the rows later scripts appended
directly to `_final`.

Measured cost of running it on 2026-08-08:

```
ledger rows                 20,559 -> 19,232   (-1,327, all LOST not moved)
village corporation links      865 ->    414   (-451)
   of the lost ANVC links: 121 were tier A
   methods: cross_dataset_propagation 224, agent_research_two_leg 121,
            agent_research_one_leg 106
```

`tier_A_ruled` rose 1,465 → 1,504, so the rulings *did* import — but the cost
was 1,327 rows of other agents' work. **Restored from
`.bak_2026-08-08_pre09`; the guard confirmed clean afterwards.**

This is the same shape as the Kootenai regression already in this file: 09
rebuilds from `_tiered`, script 50 patched only `_final`, and the rebuild
silently reverted it.

**Before running 09 ever again, one of these must be true:**
1. `_tiered` has been brought forward to contain everything `_final` holds, or
2. rulings are applied to `_final` IN PLACE without a rebuild.

Option 2 is what `code/120_normalize_rulings.py` should feed — it normalises
every inbox shape into the `review_id` format 09 expects, but **its output
still needs an in-place applier, not 09 itself.**

Always: back up `_final` first, run `62_no_regression_check.py` after, and
restore on any FELL line. That sequence is what caught this.

### `01_build_entity_spine.py` IS UNSAFE TO RUN
A full rebuild **drops every appended entity** — the village corporations, NHOs, TCUs, CDFIs, BIE schools and UIOs added by scripts 52, 61, 73, 75. Append-merge only. Re-read the spine immediately before writing so a concurrent agent cannot be clobbered.

### THE CONTAINMENT DEFECT — five independent failures on 2026-08-06
`resolve_entity`'s containment tier matches whenever one name's token set contains the other's. That is wrong in **both** directions and has now cost real money five times in one day:

| Direction | Failure |
|---|---|
| Entity ⊂ record | `CHICKASAW NATION` → *Chickasaw Children's Village*, carrying **$2.8B onto a school** (Yakama $917M, Blackfeet $568M likewise; first pass totalled **$13.4B, mostly other people's money**) |
| Record ⊂ entity | `NATIVE VILLAGE OF ELIM` → *Elim Native **Corporation*** — containment rewards the SHORTEST spine name, and in Alaska that is usually the ANCSA corporation |
| Cross-state | `Indian Pueblo Cultural Center` (NM) → *Makaha Cultural Learning Center* (HI) |
| Cross-class | `Sequoyah High School` (Cherokee Nation, OK) → *Sequoyah Fund Inc.* (a North Carolina CDFI) |
| Trap tokens | *United* / *San* / *Little* — United Tribes Technical College → United Auburn; San Carlos Apache College → Pueblo of San Felipe |
| Program entity ⊂ tribe | **Every one of 148 TDHEs resolved onto its own tribe** — `Blackfeet Housing Program` → the Blackfeet Tribe. The spine holds no TDHE, so a "successful" match was guaranteed to be wrong |

**Until it is fixed centrally, containment may be used only to resolve an owner already named in evidence — never to detect a match, and never to key a dollar.** The guards that work: require the record to be at least as specific as the entity; require a state agreement; restrict parents to government-class rows; refuse where the shorter name is a corporation and the longer is a village government.

Two guards were built, **measured, and removed because they lost**: a trap-word-dropped rule cost 130 correct rows to save 4, and an unrestricted specificity rule cost 582 to save 190. Do not re-add them.

### HIERARCHY: we own the TOP, the tribe owns the INSIDE

Elijah, 2026-08-06: *"i wouldnt trust hierarchies cuz they arent consistent, but we should trust ours — the ultimate entity `parent_native_entity` or `parent_native_org` — but underneath it only the tribe can verify the hierarchy."*

Two different claims with two different standards, and they must never be published at the same confidence.

**The top level is OURS to determine and publish.** Which Native entity ultimately owns a firm — `parent_native_entity` / `ultimate_parent_entity_id` — is what the crosswalk exists to establish, built from hand rulings, retrieved ownership documents, and firm declarations. That is the product.

**Everything BELOW the top level is UNVERIFIED unless the tribe says otherwise.** Which subsidiary rolls up through which intermediate holding company, in what order, is internal corporate structure. **Only the tribe or the entity itself can confirm it.** We may record an intermediate `parent_entity_id` as an observation, but it publishes as tier B and never as a settled org chart.

**Federal hierarchy fields are EVIDENCE, not AUTHORITY.** FPDS `ultimate_parent_uei` is a firm's self-declaration, it is inconsistent between filings, and — already recorded in this file — **FPDS does not update retroactively when ownership changes**. So:

- Use `parent_uei` to GROUP candidates and to find families. That is what it is good for.
- Do NOT publish `parent_uei` as our statement of the hierarchy.
- Where a federal parent field disagrees with a tribal source, **the tribal source wins** and both are recorded.

The practical rule for any roll-up: **group by `ultimate_parent_entity_id`, publish at that level.** Intermediate levels are for investigation and go to `review/` for the tribe to confirm, not into a published structure.

### TWO FINDINGS THAT OVERTURN WHAT WE THOUGHT (2026-08-07)

**1. `entity_hierarchy.csv` contains NO ownership chain.** Its
`ultimate_parent_entity_id` is **self-referential on 930 of 952 rows** and equal
to `parent_entity_id` on the other 22. **Zero `owned_by` edges could be derived
from it.** Every real tribe→company ownership fact lives in the identifier
ledger, not the hierarchy file. **Do not build a roll-up on that file.** It is
also stale — 952 rows against a 1,310-entity spine, missing all 185 BIE schools,
64 CDFIs, 43 UIOs, 37 TCUs and 29 Native financial institutions.

Its `parent_entity_id` mixes two incompatible facts, and mapping it wholesale to
`subsidiary_of` would have rolled 22 constituent bands into their umbrella
tribes. The typed migration (`data/clean/entity_relationships.csv`, 2,292 edges)
is now the source of truth: `owned_by` 1,462 · `associated_with_region` 391 ·
`affiliated_with` 148 (TDHE) · `brand_of` 106 · `village_corporation_for` 77 ·
`operated_by` 56 · `chartered_by` 30 · `constituent_band_of` 22. No
`subsidiary_of` edges exist, because the column held no corporate subsidiarity.

**Measured payoff of typing it:** $0 rolled through non-ownership edges, while
**174 such edges sit on entities holding $57.04B** that a flat parent column
would have moved — $32.87B via `associated_with_region`, $23.91B via
`village_corporation_for`, $264M via `constituent_band_of`.

**2. THE SPINE HAS 161 SHORT-NAME COLLISIONS, AND THEY LOOK LIKE RESOLVER BUGS.**

Two independent builds reported "a `resolve_entity` defect" on the same cases.
**Both were wrong, and patching the resolver would have broken a correct
component.** Verified against the raw spine, `resolve_entity` handles all of
them correctly.

The real cause is a spine data collision:

```
TRBF-SNJUAN-00   canonical_name    = "San Juan"
                 fr_official_name  = "San Juan Southern Paiute Tribe of Arizona"
```

The spine's "San Juan" **is** the Arizona Paiute tribe. A NAGPRA notice saying
*Pueblo of San Juan* means Ohkay Owingeh (New Mexico), which is separately in the
spine as `TRBF-OKYOWG-00`. The resolver matched the entity whose name it was
handed. It did exactly what the data said.

**161 entities carry a 1-2 word canonical name expanding to a 5+ word official
name** — Blackfeet, Bay Mills, Cabazon, Big Sandy, Bear River, Augustine, Cahto.
Each is a collision waiting for the right input string.

**So: before reporting a resolver defect, test the case against the RAW spine.**
If the resolver returns the right answer there, the defect is in the caller's
view or in the spine, not in the resolver. Standing rule 8 exists because
re-implementing matching guarantees drift; blaming the shared matcher for a data
problem is the mirror-image error.

### NEW ENTITY CLASS: individually Native-owned business (ruled 2026-08-07)

Elijah, ruling on Hidden Water Inc: *"individual Native American owned — to the
extent we identify individual native owned businesses might as well add them as
a category, and if people want to be added gives them a centralized source to do
so."*

**This reverses a standing exclusion, and the reversal is deliberate.** The
`hci_analysis.do` per-UEI drops exist to separate *tribally owned* from
*individually Native-owned* — dozens of "owned by individual Cherokees" rulings.
Those drops were correct **for their purpose** (a study of tribal government
economic activity) and are still correct for any tribal roll-up.

But an individually Native-owned firm is not a false positive. It is a
**different, real category** that nobody has assembled, and the exclusions we
already hold are the seed of it — a hand-verified list built as a by-product of
ruling them out.

**The rules that keep this from corrupting tribal attribution:**

- It is its own `entity_class`, never merged into a tribe's ownership.
- `parent_native_entity` stays **NULL**. There is no tribal owner, and inventing
  one is exactly the containment defect.
- It **never rolls up** to a tribe, an ANC, or an NHO. `bears_ownership()` has
  no edge to carry.
- Every tribal/ANC total published to date remains correct and unchanged —
  these firms were never in it.
- Evidence is the firm's own statement of Native ownership, quoted verbatim
  with its URL. Measured examples: Hidden Water, All Cities Enterprises
  ("Being Of Cherokee Indian descent…"), Mitchell Consulting, Northcon,
  Diversified Service Contracting.

Ruling vocabulary: `OWNER_NAMED` with a note beginning "individual native"
means this class, **not** a tribal owner. A note naming a tribe or corporation
(CALISTA, Bering Straits, Native Village of Eyak) is tribal/ANC ownership and is
tier A tribal attribution.

**Measured on the first 15 rulings:** tribally/ANC owned 7,329 rows / $2.76B ·
individually Native-owned 14,029 rows / $0.98B. The individual class is
**larger by row count** than the tribal one in this sample — which is why it
was worth making a category rather than a discard pile.

**Product note:** a published register of individually Native-owned firms gives
those firms somewhere to be listed, which makes it partly self-maintaining.

### CONFIRMED: the San Juan collision (2026-08-07)

Elijah, ruling on Tc&S/F-W: *"Ohkay Owingeh — tsay is a portfolio of companies
that link to Ohkay Owingeh, or formerly known as San Juan Pueblo."*

This independently confirms the spine collision found the same day. `Tsay` firms
belong to **Ohkay Owingeh (`TRBF-OKYOWG-00`, New Mexico)**, and the spine's
short name `San Juan` is `TRBF-SNJUAN-00` = **San Juan Southern Paiute Tribe of
Arizona**. Two different tribes, two states, one string. See the 281 staged
collisions in `review/spine_short_name_collisions_2026-08-07.csv`.

### Attributability is a TIER, not a yes/no
Pre-2007 assistance has no modern identifier but is **100% populated on recipient name, type and state**. Treating "no identifier" as "cannot attribute" once wrote off six years of the dataset. This dataset now has **two floors**: identifier floor (tier A) FY2007, name floor (tier B) FY2001. Never pool them in one confidence claim.

### NEVER KILL BY IMAGE NAME ON A SHARED MACHINE (2026-08-07)

An agent ran `taskkill /F /IM python.exe` **twice** to stop its own slow job and
killed four other agents' work in the process — the declination OCR workers, the
consultation build, the OIRA/hearings build and the earmarks build. It could not
see them; nothing about `python.exe` says whose job it is.

**The rule: enumerate with `Win32_Process`, match on `CommandLine`, kill by
PID.** Never `/IM`, never `pkill python`. This machine runs many agents at once
and every one of them is `python.exe`.

```powershell
Get-CimInstance Win32_Process -Filter "Name like '%python%'" |
  Where-Object { $_.CommandLine -like '*<your script name>*' } |
  ForEach-Object { Stop-Process -Id $_.ProcessId -Force }
```

Related, already recorded under standing rule 9: `ps aux` cannot see command
lines on Windows, which is why `Win32_Process` is the only reliable way to tell
your own process from someone else's.

Also: **the numeric script prefix no longer guarantees a unique step.**
`95_parse_compact_terms.py` and `95_wayback_az_gaming_status.py` both exist.
Check `ls code/<n>_*` before claiming a number.

### SOURCE COVERAGE GAPS THAT LOOK LIKE COMPLETE DATA (2026-08-07)

**Congress.gov publishes NO Senate witnesses.** Across all 17,859 committee
meetings, every populated `witnesses` array is a House meeting. A hearings
dataset built from Congress.gov alone ships with **zero Senate Committee on
Indian Affairs testimony** and looks complete while doing it. Senate witnesses
must come from **GPO govinfo CHRG MODS**. Final split after supplementing:
1,731 House / 947 Senate.

**reginfo.gov serves no OIRA meetings before 2014** (measured with month-level
probes back to 2005). An OIRA series that starts in 2014 is the source's floor,
not ours.

**Do not restrict a hearings pull to the Indian Affairs committees.** Indian
Affairs is only **30.0%** of Native hearing appearances (799 of 2,667). The rest
sit at Appropriations (504), Natural Resources under three historical names
(694), Financial Services, EPW, Commerce, ENR, Banking, Homeland Security,
Foreign Affairs, Veterans' Affairs, Education, Judiciary, Small Business and
Agriculture. Restricting by committee reproduces the set-aside-filter error in a
new place.

### `core()` FOLDS AWAY THE WORD THAT DISTINGUISHES (2026-08-07)

`core()` dropped `indian` as a generic token, so **National Education
Association resolved to National Indian Education Association** — two entirely
different organisations whose names differ by exactly the word that was folded.
Same class as stripping the Federal Register's own parenthetical disambiguator
("Oneida Nation (previously listed as ... of Wisconsin)") and landing on the
wrong Oneida.

**The rule: a token that appears in one name and not the other is never noise.**
Folding is for punctuation, corporate forms and diacritics — never for a word
that carries identity.

Also caught in the same build: `nation` matching inside `National`;
`Org, City, ST` strings leaving the **city** as the organisation (a police
department and a poultry company filed as tribal testimony); and a MODS
`<heldDate>` parsed out of a bill title dating a 2009 hearing to **1933**.

### A MARGINAL RATE CANNOT BE INVERTED (2026-08-07)

The most dangerous error found today, because the arithmetic is right, the
citation is right, and the answer is wrong by an order of magnitude.

California marks 51 compact rates `INVERTIBLE_FLAT_RATE`. Joining them to RSTF
receipts produced **795 publishable-looking tribe revenue figures**. Reading the
quotes one at a time showed **every single one is a MARGINAL base**:

> "of its Net Win from the operation of Gaming Devices **in excess of** three
> hundred fifty (350)"

> a fixed annual sum plus 15% on "the **additional** Gaming Devices"

San Manuel: `$19M receipt / 15% = $126.7M` would have shipped as that nation's
annual Net Win. **The true figure is far larger** — the rate applies only to
revenue above a threshold, so dividing recovers the *excess*, not the total.

**The rule: before inverting any rate, read the base clause for `in excess of`,
`above`, `additional`, `over`, `beyond`, or a bracket schedule.** A flat rate
divides; a marginal rate does not. Where the base is marginal the result is a
**lower bound on the excess**, never the base itself.

Final California state after the guard: **0 derived revenue rows**, 9,222
`TRIBE_LEVEL_REVENUE`, 938 `BOUNDED_DERIVED_REVENUE` each naming its blocker.

Related, same build: **CGCC suppresses some tribes' amounts** from 2016 —
prints `--` and reports them only in an "Aggregate Total for Tribes" line. 318
rows carry `value_suppressed_by_regulator` with a blank value; the aggregate is
kept typed as `aggregate_of_suppressed_tribes` and **never attributed to a
tribe**. And **SDF does not name the tribe** — it is county → local agency →
project, so it is not facility-attributable and is never summed with RSTF.

### A FISCAL SPONSOR IS NOT THE PROJECT IT SPONSORS (2026-08-07)

The largest lobbying figure recovered from the grantee 990 pull is
**$43,568,567 on the TY2024 return of New Venture Fund** (EIN 20-5806345) — a
Washington DC fiscal sponsor with roughly $900M of expenses.

The philanthropy queue proposes `NATIVE_ORG` for it, on the strength of First
Nations Development Institute's profile for *Alaska Native Birthworkers
Community* — which is a fiscally **sponsored project**, not the filer.

**The project is Native. The legal person that filed the return is not.**
A fiscal sponsor holds the EIN, files the 990, and reports the lobbying; the
sponsored project has no separate legal existence. Attributing a sponsor's
$43.5M to Indian Country because it hosts a Native project would be a
catastrophic false attribution, and it would look well-sourced.

**Rule: an EIN-keyed filing fact says nothing about the Native status of the
filer.** `np_grantee_financials.csv` records filing facts only and asserts no
Native status. **17 recipients whose Native typing rests on a proposed ruling
AND now carry a 990 lobbying figure are in the review queue with the dollar
amount attached** — those need rulings before any of it publishes.

Related trap from the same build: **The Nature Conservancy's TY2019 return
reports the identical $8,086,325 on Schedule C Part II-B AND on Part IX line
11d.** Both parse correctly; summing them invents $16.2M. The two columns stay
separate and are never added.

### A RECEIPT IS NOT AN OBLIGATION (2026-08-07)

The Florida build constructed `Net Win <= payment / rate_min`, published it in a
draft, and then **killed all 44 rows** — because the source falsified it.

The bound is true of the **obligation**. Florida EDR publishes **receipts**.
FY2013/14 receipts of $237,312,301 imply a ceiling of $1.978bn, while EDR's own
Net Win for that year is **$2.098bn**. The bound is violated by the publisher's
own figures. EDR states the mechanism: *"True-up payments generated from
activity in any Fiscal Year are received in the following Fiscal Year."*

**So before inverting any payment, establish whether the figure is what was
OWED or what ARRIVED.** A cash-basis receipt series lags the accrual it derives
from, and a bound built across that gap is arithmetically sound and factually
wrong. The arithmetic now lives in `bound_basis` on every payment row instead of
producing a bound.

This is the third distinct way a rate inversion has failed today:
1. **marginal base** — "in excess of 350 devices" (California, 795 rows)
2. **graduated schedule read as a flat rate** — New Mexico's spelled-out
   brackets, and Florida's 10% which is the bottom tier of a graduated schedule
   for one game category under a $2.5bn guaranteed minimum
3. **receipts vs obligation timing** — the above

`compact_structured_terms.csv` still marks Florida `revenue_sharing_rate = 10`
as `INVERTIBLE_FLAT_RATE`. It is not. Review item
`FL-COMPACT-RATE-10PCT-INVERTIBILITY`.

### SOURCES THAT ARE CLOSED BY RULE, NOT BY GAP (2026-08-07)

- **MSRB EMMA blocks automated document access.** Its entire robots.txt is
  `User-agent: *` / `Disallow: /*.pdf$`, and official statements are PDFs. Bond
  disclosure requires a **user-mediated** pull, not a scraper.
- ~~**Tribal Single Audits are withheld at the Federal Audit Clearinghouse.**~~
  **CORRECTED 2026-08-12 — this generalised one auditee's election into a rule
  about Indian Country, and the correction is worth more than the original
  finding.** Seminole Tribe of Florida (EIN 59-1415030) files every year,
  audited by Deloitte, and all ten filings FY2016–FY2025 are `is_public: false`
  under **2 CFR 200.512(b)(2)**. But that rule is an **opt-out**, not a bar: an
  Indian tribe or tribal organization *may elect* not to authorise public
  availability. Measured on `api.fac.gov`: **6,774 `entity_type = tribal`
  records, of which 2,046 (30.2%) are `is_public = true`** and their
  reporting-package PDFs download — Sault Ste. Marie, Mississippi Band of
  Choctaw, Muscogee (Creek) Nation, Gila River, Turtle Mountain, Quapaw,
  Robinson Rancheria. The withholding is also **per endpoint**: for a withheld
  filing the narrative tables return 0 rows and the PDF 403s, but
  `federal_awards` returns the full SEFA (127 rows for Seminole FY2022). See
  `docs/GAMING_FINANCIAL_EXHAUST_BUILD_LOG.md`.
- Rating-agency pages are JS shells — Fitch's Seminole entity page returns
  1.3 MB containing "Seminole" **zero** times.

### A BROKEN SEARCH IS NOT EVIDENCE OF ABSENCE (2026-08-07)

South Dakota's `dor.sd.gov/search/` returns **zero results for `casino`** — a term
demonstrably present across that same site. The search index is broken. Three
captures of it are retained as evidence of the *search behaviour* and must never
be cited as evidence that South Dakota publishes nothing.

Same class: Kansas's sitemap returns HTTP 200 with **zero entries**; Oregon's
404s; Arizona's 478-URL sitemap contains **zero** tribal pages. A site's own
navigation failing is a fact about the navigation.

**Distinguish three states in every coverage table**, because they look
identical and are completely different facts:

| | Meaning |
|---|---|
| `PUBLISHES` | retrieved it |
| `WITHHOLDS` | published a statement that it will not release — e.g. Washington deems per-tribe fuel data *"personal information and exempt from public inspection"* |
| `NOT_FOUND` | swept and did not find it, **naming what was swept** |
| `NOT_CHECKED` | nobody looked |

A state that withholds by statute and a state nobody checked are opposite
findings. The first is permanent; the second is unfinished work.

### PROVENANCE: A PATH YEAR IS NOT A REPORT YEAR (2026-08-07)

Minnesota LRL's URL path year runs **one ahead** of the report year throughout
the series — the 2014 report sits at `/docs/2015/mandated/150425.pdf` and the
2025 report at `/docs/2026/`. A file named from its path segment was off by a
year. Renamed; never infer a report year from a URL path.

Related, from the same sweep: several retrieved PDFs are **image-only scans with
no text layer** — that Minnesota report yielded 185 bytes of extracted text, and
both Colorado 1995 compacts yielded 38 and 48 bytes. A near-empty extraction is
a scan, not an empty document, and must be recorded as such rather than read as
"nothing in it".

### TWO FILES THAT DO NOT CONTAIN WHAT THEIR NAME SUGGESTS (2026-08-07, script 111)

**1. The identifier ledger's EIN leg is a candidate list, not an attribution.**
Of the 1,104 `identifier_type = EIN` rows in
`cedar_identifier_ledger_final.csv`, **1,085 carry `attribution_method =
need_v6`** — which `cedar_domain.METHOD_ACCURACY` records at **6.5% accurate** —
and **not one EIN row is `confidence_tier` A** (1,044 B, 4 C, 56 X). Measured
misfires: `UNITED WAY OF CAYUGA COUNTY` and `UNITED WAY OF THE GREATER CHIPPEWA
VALLEY` both → *United Auburn* on the trap token `united`; `YAVAPAI COMMUNITY
HOSPITAL ASSOCIATION` → *Yavapai-Apache*; `FIRST UNITED METHODIST CHURCH OF
PEORIA` → a tribe. **Never use an EIN→tribe_id row from this file as evidence
that an organisation is Native.** An X-tier row is a negative ruling and must
never resurface through it either.

**2. `native_entity_lobbying_disclosures.csv` contains no nonprofits.** Its
27,796 filings key only to governments and corporations — TRBF 23,942, ANRC
2,002, AKNF 587, SGVF 238, TRBS 100, CNSF 72, CNSS 14. **Zero of the spine's 55
Intertribal Organizations appear in it.** NCAI, NIGA, USET, NIHB, NARF, NAIHC
and NCUIH lobby heavily and sit in `lobbying_unmatched_clients.csv` instead.
Any question about *organisational* Native advocacy must read the raw corpus at
`code/lobbying_pull/raw_filings.jsonl` (39,448 filings, client-level, with
specific-issue text and government entities), not the keyed file.

Related, measured on the same run: **LDA client state is the FILING address,
not the client's.** On the 25,719 keyed rows carrying both, client state and
entity state agree on 91.8%, and 941 of the disagreements are `DC` — the
registrant's office. State agreement is corroboration on an LDA row, never a
second leg strong enough for Tier A.


### A SET-ASIDE IS A PROPERTY OF THE AWARD, NOT OF EACH MODIFICATION (2026-08-08)

**This nearly corrupted the project's flagship statistic.**

The USAspending archive reports set-aside per TRANSACTION and leaves it blank on
**56% of rows**. `master prime file.dta` carries the AWARD's value on every row
of that award. Read transaction-level, the two disagree on **59.6% of shared
contracts**, and **4,580 contracts the `.dta` calls 8(a) land in "None
reported."**

Published naively, that would have **inflated the "no Native preference" share**
— the 60.9% / $86.19B finding — purely on a definition change between sources.
The number would have moved, looked like a discovery, and been an artefact.

**Fill set-aside forward from `contract_award_unique_key` across all years
before computing any preference share.** Within a single year the fill has
nothing to find, which is itself an argument for pulling the backfill years.

### A DROPPED CONNECTION IS NOT A 404 (2026-08-08)

`head()` returned 0 for both a genuine 404 and a transport failure, and the
caller read 0 as "not published." When the host began refusing, the pull
**raced through 19 years in five seconds** — issuing HEAD requests at a host
that was refusing us *for request rate*.

**Distinguish transport failure from HTTP status.** A 0 is stop-work and must
back off; a 404 is a fact about the object. Refused objects are recorded as
`http_status=0` **with the reading spelled out**, so absence is never inferred
from a block.

### Traps that will bite a new agent
- **`faads_transactions.csv` is a strict subset of `faads_transactions_all_agencies.csv`** (all 59,514 keys checked). Reading both double-counts $53M.
- **`Navajo_Operation` in BIE data is an administrative grouping, not ownership.** Trusting it books 35 schools to the Navajo Nation.
- **56 federally operated BIE schools must NOT roll up to any tribe.** Their blank parent is a ruling, not unfinished research.
- **Use `yea`/`nay`, never `voteview_yea_count`** — Voteview under-counts the 103rd Congress's Delegates.
- **Absence under a filter is a property of the filter.** 60.9% of the Native contracting dollars we can identify report no Native preference at all.
- **CHECK THE HTTP STATUS, NOT THE FILE.** A 404 body from bia.gov still contains `<main>`, so a parser that trusts "the file has content" will happily ship a region with **zero agencies** and no error. The BIA Southwest Region's agency page lives at a different slug (`/southwest-region/agencies`); the obvious URL 404s. Record status per file in the fetch manifest and refuse anything that is not 200.
- **A source disagreeing with ITSELF is a finding, not a bug to smooth over.** BIA's own sentence says "83 agencies"; its twelve regional sites publish **87** offices. Both numbers are recorded, neither was adjusted to meet the other, and `office_type` explains the gap (80 agencies, 4 field offices, 1 irrigation project, 2 that are neither).
- **Never rule a HISTORICAL record against a CURRENT web page.** Three gaming rulings were withdrawn on 2026-08-06 for exactly this: MidJim ×2 and Seminole Nation Travel Plaza were ruled "not a casino" against 2026 pages, but they are Casino City records that **closed in 2003–2005**. A 2026 page cannot testify about a 2003 property. Check the record's own close date first.
- **Read the source's own disclosure columns before searching the web.** The votingpatterns roster carried a `notes` column saying *"Same property"*, *"Adjacent to Grand"* in as many words. The duplication was disclosed at source and had never been read; a web sweep would never have found it. This resolved 14 of 23 undated rows with zero new research.
- **A vendor list's scope changes what a row means.** Casino City is a *gaming* roster — its Montana section carries `Dad's Bar` and `TJ's Quikstop` because those are licensed video-gambling locations. A tribal convenience store appearing in it is evidence **for** gaming, not against.

## Canonical vs. deprecated files
- `bgov_tribe_analysis_120321.dta` = authoritative. **`bgov.csv` is a lossy export** (inflation factors truncated to integers on all 878 rows). Never analyze the CSV.
- `tribal_level_obligations.dta` = canonical panel. **`final_analysis.dta` is an earlier vintage** (2021-base series NaN on FY2022 rows; 1,590 cells of deflator drift). Use the **2022-base** series only.
- 117 panel rows carry `qc_flag` (deflated value inconsistent with nominal × deflator, e.g. Alabama-Quassarte 2018). Do not use flagged rows until reviewed against the do-file.
- **The analysis do-file has never been provided.** The ANC/NHO identification logic Elijah remembers lives in its comments. Ask for it; do not assume its contents.

## Identifier strategy (settled)
- **NEID (CICD Native Entity Connector Crosswalk, Feb 2026) SEEDED the entity spine** and is no longer its full extent (see Current State: 1,310 entities). 687 entities as delivered, 7 prefixes (TRBF/AKNF/TRBS/CNSF/ANRC/SGVF/CNSS). 565 already written into Entity_Master col T by exact-name match; ~215 need a fuzzy/manual pass.
- **CAGE-first, then UEI.** Per HigherGov (Siken): "naming doesn't impact mappings — everything is mapped off the UEI (or CAGE or DUNS)." DUNS died April 2022; CAGE persists across the transition. Map CAGE→UEI via SAM entity extract.
- FPDS pulls come two ways (Siken emails, in Source_Registry): **flag-at-award** (FPDS socioeconomic flags) vs **SAM-registration match** (uei or ultimate_parent_uei). Use flag-at-award for status-at-time analysis. The seven flags are enumerated in Source_Registry.
- Deal rows may cite USAspending recipient profiles by CAGE/UEI search instead of archiving award documents (Elijah's convention — legitimate).

## The subtle insight (do not lose this)
Elijah's own Dippel correspondence proves that **no reliable corporate-hierarchy-over-time source exists** and that FPDS **does not update retroactively** when ownership changes. But the deal ledger built here records dated ownership changes (Chenega buys SecuriGence 6/2024; sells CFS 4/2025; BSNC buys Alaka'ina 2026; Koniag buys SoundWay 3/2026...). **The deals dataset IS the missing time-varying ownership ledger.** Joining deal dates to the identifier crosswalk makes contract attribution time-aware — the thing he told Dippel couldn't be built in general CAN be built for Indian Country, because this project maintains the M&A event stream. Every acquisition/divestiture row should eventually emit an ownership-change record (entity, counterparty, effective date, direction). This is a genuinely novel research asset and a Lumecon moat ("capture once, reuse everywhere").

## Coverage truths (verified, sometimes contra memory)
- BGOV crosswalk = **tribes/tribal enterprises only. No ANCs** (audited; Elijah's memory said otherwise).
- Obligations panel = lower-48 by design; no ANCs; short-form tribe names (only 15 exact-name overlaps with BGOV's long forms — same universe though: top tribes match across independent builds, which is the strongest validation in the project).
- FPDS self-certification flags **undercount**: BGOV found 241 contracting tribes vs 588 recognized entities. SAM-registration matching plus the Entity_Master alias list closes the gap.
- The `contract-03-18-*.csv` (4,000 rows) is **one corporate family** (28 awardee UEIs, 1 ultimate parent, $1.85B) — a sample export, not the comprehensive pull. Do not treat it as the universe.
- NHO universe ≈ 30–40 (Elijah's estimate); 7 seeded from NHOA board; complete via SBA DSBS 8(a) NHO-owned list. Alaka'ina Foundation (NHOA board) = seller family in ND-2026-011.

## Deal-ledger conventions
- **Dates:** prefer transaction/closing > official announcement > publication. Month-level allowed with a mid-month placeholder ONLY if `Date_Basis` discloses it. Never invent a day silently.
- **Scope windows are strict:** the Lumbee land buys closed Dec 2025 → excluded from 2026 and recorded in 2025. Document reviewed-and-excluded items in audit notes (contamination prevention).
- **Aggregates:** formula rounds (IHBG) = one portfolio row; competitive rounds with published lists (RTA) = row-per-award. TSAF precedent for aggregate + recipient list in Notes.
- **Divestitures count** (Native entity as principal). Milestone rows must not double-count project values (INSPIRE note).
- **Threshold:** $1M default; sub-$1M rows need `Threshold_Exception=Yes` + rationale.
- Summary sheet is **formula-driven with fixed label lists** — new categories/source-types require adding a label row or they silently drop from rollups. Historical sheet is deliberately excluded from the 2026 Summary.
- Always: recalc via LibreOffice script after edits; append Quarterly_Update_Log run row (next: RUN-2026Q3-012) + Audit_Log entry; verify counts programmatically before shipping.

## Access quirks (hard-won)
- **ntia.gov / broadbandusa.ntia.gov block automated fetch**; press mirrors strip award tables. TBCP's 274 awards (~$2.2B) need manual download → upload. **Uploaded files bypass all robots restrictions.**
- hud.gov fetches OK but the 2025–26 reorg 404'd archived ONAP award PDFs — locate via Codetalk archive or web.archive.org manually.
- Sandbox bash reaches only the allowlist (github/raw.githubusercontent/pypi...) — the cisagov TLD mirror and CICD repo clone this way. USAspending API is POST-only + non-allowlisted: pulls happen outside, results come in as uploads.
- web_fetch only accepts URLs already surfaced in-conversation (search first, or have Elijah paste the URL).
- Entity newsroom sweeps yield ~3–4 verified deals per corporation searched (Koniag/Sealaska/Chenega proven). ~15 high-flow newsrooms unswept: Doyon, NANA (pre-Drake), Ahtna, BBNC, Afognak/Alutiiq, UIC, Wind Creek/PCI, CNB, CNI, Ho-Chunk Inc., Gun Lake, Waséyabek.

## Matching pitfalls (from Elijah's lobbying memo — apply everywhere)
Name similarity ≠ relatedness ("Cherokee Inc." trap). DBA ≠ legal name. Subsidiaries don't share parent names. Firm ≠ establishment. Identifiers change on ownership events. Therefore: match conservatively, leave ambiguous blank and flagged (the 34 unmatched BGOV tribes and 3 corrected village-corp region mappings are the model — my own auto-matcher produced Sea Lion→Koniag via a token trap; audit every automated match against ground truth).

## Queue (highest value first)
1. Get the **do-file**; review the 117 QC-flagged panel rows against it.
2. Comprehensive FPDS pull (both methodologies) via HigherGov/USAspending → upload → match through Entity_Master aliases + NEID; build the ownership-change ledger from the deal rows.
3. TBCP + HUD ONAP award lists via manual download → row-per-award (path to 500+; channel inventory with counts lives in Backfill_Plan).
4. Finish NEID fuzzy pass (~215), resolve 34 BGOV unmatched tribes, complete NHO universe, UEI-map the crosswalk CAGEs via SAM extract.
5. Historical year sweeps per Backfill_Plan (reverse-chronological: 2025 first — link rot punishes delay).

## Do-file findings (hci_analysis.do, read 2026-07-31)
- **Identification = Conditions 1–3**: (1) hand-built shortname list from Federal Register tribe names matched against `parent_name`; (2) tribe abbreviations/common enterprise names; (3) Native-related words — used only to refine 1–2, then dropped. Discovery of residual candidates restricted to Buy Indian / 8(a) / Indian Business set-asides → tribally-owned firms with non-obvious names winning only full-and-open contracts can be missed (quantifiable undercount direction).
- **ANC/NHO answer (settled):** the code identifies lower-48 tribes ONLY. ANCs appear solely as exclusions (e.g., Ahtna JV drop); **no NHO identification exists anywhere in this code.** The remembered "Alaskan Natives and NHOs identified" is not in this file.
- **The evidentiary gold**: dozens of per-UEI drops, each with a citation (cage.dla.mil, GAO decisions, OpenCorporates, archived sites) distinguishing *tribally owned* from *individually Native-owned* (the many "owned by individual Cherokees" drops) — the operational form of the "Cherokee Inc. trap." Preserve these UEI-level rulings; they are irreplaceable manual work and should be imported into Entity_Crosswalk as an exclusion table.
- **BUG FOUND (probable cause of the 117 QC flags):** in the `comparisoncicd` block, `gen all_obligations2021 = i_total_obligations2021 + i_total_obligations_idv2022` **adds 2021-base and 2022-base series** — a mixed-deflator sum feeding the CICD comparison. Audit every `all_obligations*` construction for base-year consistency before reuse.
- Deflators: FRED CPIAUCSL annual avg, `inflfac = CPI[last]/CPI` — confirms the continuous factors in the .dta and re-confirms bgov.csv's integer factors as export corruption.
- Provenance note: built in the Winnebago/HCI project context (raw = "Data Request 4-5-2023 File 1.csv" from HigherGov); UEIs verified via cage.dla.mil.

## Addendum (2026-07-31, late): three more files reviewed
- **ANC rule-out question SETTLED across all four .do files:** no extensive ANC rule-out commentary exists anywhere. `playground.do` is not code — it is the 230-tribe shortname→ID key underlying the obligations panel (the panel's entity list source). `hci_prelim_analysis.do` (Ho-Chunk visit figures, Mar 2023) contains no ANC logic. The ONLY ANC handling in the corpus = the few per-UEI drops in hci_analysis.do. The remembered commentary does not exist in the provided files; if it exists at all, it is in a file not yet shared.
- `hci_prelim_analysis.do` bonus: the Ho-Chunk Inc. / All Native Group name-standardization block ("Wincomp L L C Dba All Native" → Wincomp LLC, etc.) is a worked example of DBA-variant collapse — reuse the pattern for other families.
- **CICD_NACA_Presentation.pptx received but NOT yet ingested** (needs pptx skill pass) — first action next session; it may contain the ANC/NHO identification Elijah remembers, from the CICD side rather than his code.
- Spider-web seeding status: 878 tribal CAGEs (Entity_Crosswalk) + 28 UEIs/1 parent UEI (FPDS_Entity_Extract) + 623 entity domains = seeds exist; one parent UEI provably pulls a whole family (28 children observed).

## AI-native data layer (redesign, 2026-07-31)
- `/data/*.csv` is the **canonical machine layer**: deals_2026_ytd, deals_historical_2020_2025, entity_master, entity_crosswalk_bgov, reconcile_queue. The xlsx is the human/presentation layer. Agents: read/patch CSVs, then sync to xlsx; never parse the xlsx when a CSV exists.
- **Reconciliation protocol** (Elijah's terminal loop): agents append uncertain entities to `reconcile_queue.csv` (issue_type, entity_name, evidence, question, YOUR_RULING). Elijah fills YOUR_RULING fast; next session imports rulings as permanent per-entity decisions (same jurisprudence model as the do-file's per-UEI drops). Current queue: 321 items (214 NEID-unmatched, 73 village-corp regions, 34 BGOV tribes) + 5 unsourced 2020 deals caught by the final audit (MA2020-001, MA2020-013, ACQ2020-018, ACQ2020-020, ACQ2020-022 — now marked UNSOURCED in the workbook).
- **Naming-pattern rulebook (memorialize + extend):** ANC/NHO parents carry distinctive Alaska Native / Hawaiian names (Ukpeaġvik, Alakaʻina, Nakupuna) → high-precision matches. Subsidiaries invert this: often generic names, frequently numbered series ("<Parent> One LLC", "<Parent> Two"), DBAs (Wincomp LLC dba All Native). Rule: NEVER classify by subsidiary name alone; resolve via ultimate_parent_uei / SAM hierarchy, then record the family. Individual Native ownership ≠ tribal/ANC/NHO ownership (Cherokee drops). New tribes are rare — recognition events (Lumbee) are the only additions to watch.
- **Funding-DTA integration (incoming):** Elijah holds a 2009–2023 lower-48 tribal federal funding panel, SAM/CAGE-crosswalked. Plan: ingest → union its UEI/CAGEs with Entity_Crosswalk → spider-web (parent UEI pulls families) → extend to ANCs (small, distinct-name universe) and NHOs (~30-40 nonprofits). Reinforcement loop: grant/contract recipients ≈ the active deal-making population, so the funding roster doubles as the systematic deal-search list, and entities absent from it get individual small-entity searches.

## Year One roadmap & publication cadence (set 2026-07-31)
**The five datasets:** (1) Deals ledger. (2) Federal contracting - PRIME awards (obligations panel + FPDS extracts; subcontracting expansion below). (3) Federal funding - assistance/grants (the 2009-2023 DTA and forward). (4) Lobbying/influence. (5) The linked analytical file - all four joined with time-aware ownership attribution. The entity universe + identifier crosswalk is not a numbered dataset: it is the SPINE underneath all five. Papers 6 and 7 ride on 4 and 5.

**Cadence:** MONTHLY data brief (light: deals captured that month, one stat or chart, entity updates worth noting - feeds Lumecon presence and keeps scrape channels warm). QUARTERLY deep refresh (the existing RUN- discipline: verification pass, one historical backfill year, reconcile-queue cycle, log entries). ANNUAL flagship report (year-in-review; grows into the Paper 6 descriptive).

**Subcontracting expansion (dataset 2), both directions:** (a) Native entities as SUBS under non-Native primes - a revenue channel the prime-award data misses entirely; (b) Native primes' own subcontractor networks - who they hire. Source: USAspending/FSRS subaward data keyed by UEI/CAGE both ways (the uploaded subcontract CSV is the template: Sub + Prime UEI/CAGE on every row). Strategic note: direction (b) is empirical input-output linkage data - observed tribal supply chains are direct evidence for TEIM leakage/multiplier structure. Dataset 2 quietly feeds the patent.

**Quarter-by-quarter:**
- Q1 (Aug-Oct 2026): stand up monthly brief; 2025 deals backfill (reverse-chron per Backfill_Plan); federal LDA pull (three nets) + client resolution begins; first reconcile-queue cycles with Elijah rulings.
- Q2 (Nov 2026-Jan 2027): 2024 + 2023 backfill; subcontracting layer both directions; funding DTA (2009-2023) ingested and brought forward.
- Q3 (Feb-Apr 2027): 2021 + 2022 backfill completes the historical ledger against the 2020 baseline; STATE lobbying begins (CA/WA/OK/AZ, gaming-ranked); lobbying trends report drafted.
- Q4 (May-Jul 2027): dataset 5 assembled (NEID joins + ownership-change attribution); annual flagship #1 published; select and scope the next three datasets.

**Next-three candidates (choose in Q4):** tribal municipal/bond finance (EMMA); land transactions & trust acquisitions ledger; gaming compacts & revenue-sharing terms; state/local procurement to Native entities; tribal employment/payroll; philanthropy & foundation grants to Native orgs; Canadian expansion (First Nations dev corps + Registry of Lobbyists).

## Gaming + compact datasets (planned 2026-07-31)
GAMING_DATASET_PLAN.md (three layers: NEPA development history / directory core / compact authorization) and COMPACT_DATASET_PLAN.md (standalone compact build with explicit merge plan) added to the candidate queue for the Q4 next-three decision. Phase-1 index scrapes for both (BIA gaming-land decisions, 138 records + compact/FR index) are one-session jobs on verified-fetchable bia.gov and can run any time; they join the deals ledger and spine immediately.

## Federal actions dataset (planned 2026-07-31)
FEDERAL_ACTIONS_DATASET_PLAN.md added: FR-based event log of formal federal-tribal actions, 1994+ (free GET API, in-session runnable). Doubles as spine maintenance (recognition list, renames, status changes) and the dating authority under deals/gaming/compacts. Q4 candidate; note gaming+compact index scrapes are FR streams, so those plans partially bootstrap this one.

## Native bills & votes dataset (registered 2026-07-31)
Dataset 10: congressional bills affecting tribes/Native entities (proposed + enacted) with roll-call votes, member positions, cosponsors. Elijah already holds a partial build (confirm House vs Senate coverage; Congress.gov API free-key covers bills/actions/cosponsors both chambers; roll-calls via House Clerk + Senate.gov XML). Research anchor: tribal influence on the Republican margin (Dem baseline ~fixed). Joins: lobbying filings' bill numbers (parsed from specific-issues text) -> bill_id -> votes = the full influence chain lobbying -> target -> outcome; FR actions dataset supplies the regulatory parallel. Catalog note: ~10 datasets planned; maintenance discipline per the pilot gates - three live and impeccable before the rest activate on subscriber demand, Grove-first debuts.

## Cedar Press launch plan & tier map (set 2026-07-31)
Launch target: Oct-Nov 2026, ahead of everything else; Dec-Jan year-in-review pieces per dataset = Q1 2027 editorial calendar for free.
**Portal tier ($499, six datasets):** 1 Indian Country Deals, 2 Federal Contracting (prime), 2b Subcontracting, 3 Federal Funding, 4 Lobbying (trends tier), 9 Federal Actions Affecting Tribal Nations (the launch-feasible pick: free GET API, weekly editorial fuel, dates/verifies the other five, year-end flagship "Every Formal Federal Action in Indian Country 2026").
**Grove-gated ($2,500, four datasets):** Bills & Votes (lobbying users' next question), Gaming Development, Compacts (deals/contracting users' next question; banker/investor buyers), Nonprofit & Philanthropy (funding users' next question; foundation buyers).
Architecture rule: every Grove dataset is the "next question" of a portal dataset - the $499 tier generates the curiosity the $2,500 tier answers. Grove-first debuts for anything new; portal additions earned by subscriber requests.

## Pull discipline — READ BEFORE ANY REMOTE FETCH (set 2026-08-05)
**`docs/PULL_DISCIPLINE.md` is mandatory reading before writing a script that fetches from a remote host.** On 2026-08-05 four agents ran concurrent pulls against `api.usaspending.gov`, the host began refusing at the edge, and each agent independently left a resumer polling every 300s — quadrupling the probe rate against a host that was blocking us *for* probe rate. No agent could see the others; the failure is structural, not careless.

The rules in short: **one poller per host, ever** — check `logs/*resume*.log` and `ps` first, and claim the host in `logs/_HOSTLOCK_<host>.json` before polling. Append your work to an existing lock's `queue` and exit rather than starting a second loop. Back off exponentially (60s doubling to 30 min, stop at ~2h), never on a fixed metronome. Distinguish an **edge block** (instant `RemoteDisconnected`/curl `000`, under 1s — stop, more requests extend it) from a **throttle** (HTTP 429 — honour `Retry-After`) from a **slow server** (timeout at 30s+ — retry is fine). Never re-submit a server-side job already accepted; persist and recover the token. Checkpoint before the first request so a killed poller loses nothing.

When blocked: probe a *different* host to confirm it is host-specific, stop all but one poller, and go do the work that needs no network — matching, codebooks, review queues, docs. **A block is a finding, worth reporting plainly with the probe evidence; it is not a failure.**


---

## SAM.gov: the rate limit is not the constraint. D&B is.

**Measured 2026-08-12, before any SAM pull.**

### The rate limit reads worse than it is

`10 requests/day` applies only to a **non-federal user with NO role in
SAM.gov**. A non-federal user *with* a role, or a non-federal **System Account**,
gets **1,000/day**.

More importantly the limit counts **requests, not records**:

| mode | cap |
|---|---|
| synchronous search | 10 records/page, **10,000 total** - useless for bulk |
| **Extract API** (`format=csv` or `format=json`) | **1,000,000 records per request** |

So even the worst tier is up to 10M records/day. **Always use the extract mode;
never paginate the synchronous endpoint for bulk.** The extract returns a
download URL containing the literal string `REPLACE_WITH_API_KEY`, which must be
substituted before the second request.

### The real constraint: D&B Open Data may not be disseminated in bulk

SAM's disclaimer defines **D&B Open Data** as: Legal Business Name, Street
Address, City, State/Province (name, code, abbreviation), County Code,
ZIP/Postal Code, Country (name and code).

It attaches to:
- entity registration records **last updated before 2022-04-04**
- exclusion records **created before 2022-04-04**
- **all base award notices with an award date before 2022-04-04**

The terms require written attribution to D&B and forbid accessing, using or
disseminating that data **in bulk** - "in amounts sufficient for use as an
original source or as a substitute for the product being licensed."

**This lands squarely on the FY2000-2007 prime backfill**, which is entirely
pre-2022 base awards, and on every pre-2022 year of any SAM contract pull.

### The rule

**Separate the contract fact from the D&B-derived entity attribute.**

| field class | example | pre-2022 SAM-sourced |
|---|---|---|
| contract fact | PIID, action date, obligation, NAICS, agency, socio-economic flags | **fine to publish** |
| D&B Open Data | legal business name, street, city, state, ZIP, country | **do not publish in bulk** |

A SAM-sourced pre-2022 row must carry a provenance flag naming SAM as the
source, so the question can be answered **per field** rather than per dataset.
Without that flag the whole file becomes unshippable the day anyone asks.

**Verified 2026-08-12: this does not touch anything currently shipped.** Zero of
20,555 ledger rows with a `legal_business_name` have a SAM source - they come
from `master_tribal_entity_registry.csv` (13,187), `need_v6_geocoded.csv`
(5,163), BGOV (878), and the contracting/funding builds. Recorded before the
pull, not after.

**Open and unresolved:** USAspending republishes FPDS base awards and does not
carry this disclaimer. Whether the D&B restriction follows the data into
USAspending's own open archive is not settled here, and should not be assumed
either way. Our existing `recipient_city_name` came from BGOV/USAspending, not
SAM.

### Also recorded

- **`api.sam.gov` returns HTTP 404 for an invalid or missing key**, not 401 - on
  every path, including ones that exist. On 2026-08-05 the same endpoint returned
  `401 API_KEY_INVALID`. **A 404 from api.sam.gov is therefore NOT evidence that
  an endpoint path is wrong.** Do not conclude an endpoint is absent without a
  valid key. Broken auth reads exactly like a missing route.
- The SAM key was **rotated 2026-07-25** and the replacement has not been
  collected. Procedure is in `docs/API_KEYS.md`: log in at sam.gov directly,
  Workspace > Profile > Account Details > **Public API Key**, eye icon, one-time
  password to email. **Do not follow the link in the rotation email.**


---

## The award archive REPLACES monthly. Probe the stamp; never hardcode it.

**Measured 2026-08-12.** Every one of the **4,597** keys under
`files.usaspending.gov/award_data_archive/` now carries the stamp `20260806`.
**Not one carries `20260706`.** The archive is not cumulative - each monthly
vintage replaces the last, so a URL that worked in July returns a **real 404**
in August.

**Decision (Elijah, 2026-08-12): enumerate the current stamp at the start of
every run.** Never pin it in code.

Two traps this creates, both already hit:

1. **A pinned stamp makes a 404 look like a fact about the year.** `FY2016_..._20260706.zip` 404s
   because the vintage rolled, not because FY2016 is unpublished. Written to a
   manifest, that becomes "the archive does not publish this year" - false, about
   an object enumerated 25 minutes earlier.
2. **Bumping the stamp GLOBALLY is worse than leaving it stale.** It relabels
   July-vintage rows already on disk as August-vintage, and it defeats the guard
   that stops FY2023/24 being appended twice. Make the stamp **per-year**, set
   from the listing that actually produced each file.

### Three failure shapes that all look like success

Found the same day, all in the puller:

- **A 500 is not a 404.** Only `404` and `403` are facts about the object.
  Everything else is a fact about the moment. FY2007's 500 was recorded as
  "not published."
- **An interruption must not look like a completion.** Extracts written straight
  to their final name and skipped on `exists()` left a **256-row** FY2011 extract
  beside ~27,000-row neighbours - skippable forever, 0.9% complete, indistinguishable
  from a finished year. Write `.part`, then rename.
- **A stalled stream is a third shape.** `timeout=1800` is the gap BETWEEN
  chunks, not a total. FY2011 died at exactly 20,971,520 bytes and sat motionless,
  burning the run deadline. Use `(connect, read)` timeouts AND check
  `Content-Length` - a truncated zip still starts with `PK`.

### Host tolerance, measured

~**1 object per 2-3 minutes**. Ten 1.4 GB objects succeeded at 2.5 min apart; six
small ones 8s apart did not. Size is not what the host is rating - request
frequency is.

---

## AN AGENCY NAME IS A LABEL, NOT AN IDENTIFIER (2026-08-12, script 131)

The archive backfill was merged into `prime_contracts.csv` on 2026-08-12
(826,637 -> 1,217,768 rows). The merge key was specified as the transaction
identity — **PIID + modification_number + transaction_number + agency**. Two of
those four fields do not exist and the fourth is not an identifier. Both facts
were measured, not assumed, and both would have shipped a wrong file.

**1. The BGOV side has no transaction identity at all.** `master prime file.dta`
has 27 columns and carries **no `modification_number` and no
`transaction_number`**. A BGOV row is an award-year-vendor aggregate: 507,564
rows FY2008-22 over 402,005 distinct (PIID, FY), 1.26 rows per contract-year.
The archive over the same years is 631,507 rows over 295,664 distinct (PIID,
FY) — 2.14 per contract-year, which is what transaction level looks like. **The
two files are not the same grain**, and no amount of keying makes them so.

**2. `funding_agency` exists on both sides and must NEVER be in a join key.**
The two sources use different vocabularies for the same office — `Us Geological
Survey` vs `Geological Survey`, `Office Of The Assistant Secretary For
Administration (Asa)` vs the unparenthesised form. Measured cost of putting it
in the key:

| key | BGOV attributed rows left unmatched |
|---|---:|
| piid+fy+uei | 584 ($0.203B) |
| **piid+fy+uei+agency** | **40,949 ($20.739B)** |

Including agency would have left **$20.5B of the same contracts counted twice**,
and the file would have looked bigger and more complete while doing it. Same
shape as the set-aside definition change already in this file: an artefact that
reads as a discovery.

**The rule: before keying on a field, check whether it is an IDENTIFIER or a
RENDERED LABEL.** PIID, UEI, CAGE and the `*_unique_key` fields are identifiers.
Agency names, office names, business-type descriptions and set-aside
descriptions are labels — each source renders them its own way, and a join on a
rendering silently becomes a join on the renderer.

**Precedence is wholesale per key, never field-by-field.** On a shared key every
BGOV row is dropped and every archive row kept. Blending a 1-row aggregate with
an N-row transaction set would invent a row neither source reported. `source_file`
is not rewritten on any row, so the seam stays visible in the data.

Verified after: **0 keys carry both sources**, FY2000-2007 and FY2023-2026 are
byte-identical to the pre-merge backup, and the guard is clean. The 584
attributed BGOV rows the archive never had are **flagged in `review/`, not
dropped**.

---

## ESM.zip was deleted 2026-08-12. It was a verified duplicate.

All **84** entries existed extracted at `data/raw/esm_hci/`, byte-size identical,
none missing - **5.52 GB duplicated**. The zip was created by us on 2026-08-05 and
freed 1.6 GB -> 6.9 GB when removed, which unblocked prime FY2007 and assistance
FY2020, both of which had failed on **disk**, not on the host.

`code/123_census_esm_raw.py` and `code/125_esm_native_entity_discovery.py` were
repointed to the extracted path FIRST and smoke-tested, then the zip was deleted.
**That order matters** - repoint, verify, then remove.

**The raw is the source of `master prime file.dta`, which is the source of our
FY2000-2022 prime rows.** Do not delete `data/raw/esm_hci/` - it holds FY1991-2023
contract transactions with the full socio-economic flag set, and it is the only
local route to FY2000-2007.

---

## THE CHEAPEST ROUTE INTO INDIAN COUNTRY'S PAPER TRAIL IS SOMEBODY ELSE'S FOIA LOG (2026-08-12)

`docs/CONGRESSIONAL_CORRESPONDENCE_FOIA_BUILD_LOG.md` and
`code/136_build_congressional_correspondence_and_foia_index.py`.

**Interior's own FOIA site publishes no logs. `doi.gov/foia/logs` is a real
404.** The logs live in each bureau's reading room, and Interior's library
page points **AS-IA, BIA and BIE at one URL** —
`https://www.bia.gov/as-ia/foia/reading-room` — which carries monthly and
annual FOIA logs from FY2017 to the current month. IHS publishes FY2020–FY2026
as clean XLSX. Those two pages are the highest-value single sources found in
this build: **every row in them is about Indian Country by construction**,
because that is the bureau's whole remit.

**And the requests in those logs are a research index.** A granted request
means the records were located, reviewed and released — the expensive part,
already paid for by someone else. E&E News files a standing monthly request to
every Interior bureau for, verbatim:

> "all records concerning all logs of correspondence that record letters from
> members of Congress to your bureau/office. The logs should detail the
> correspondence's control number, the date it was received, what congressional
> office sent it and its subject."

That single sentence proves the congressional correspondence log EXISTS at each
bureau, names the four fields it carries, and shows it has already been located
and reviewed. **Read the FOIA log before filing anything.**

### Named correspondence systems, confirmed from the agencies' own SORNs

Correspondence-management systems usually have **no public face at all**, so
the way to establish one exists is the agency's own Privacy Act System of
Records Notice in the Federal Register. Confirmed and quoted:

| agency | system |
|---|---|
| Interior | **OS-20, "Secretarial Controlled Correspondence File"** |
| EPA | **EPA-22, "Quill"** — replaced the Correspondence Management System |
| HUD | **HUD/ADM-09, "Correspondence Tracking System (CTS)"**, Office of the Executive Secretariat |
| HHS | 09-90-0058, formerly "FOIA Case Files and Correspondence Control Log" |
| DOT/FAA | 845 ACCIS, Administrator's Correspondence Control |
| USDA/FNS | FNS-22 Controlled Correspondence Files |

**Name the system in a FOIA request.** That is the difference between a search
and a "no records" closure.

### Traps this build paid for

- **`\b` treats `_` as a word character.** `foia[-_ ]?logs?\b` does NOT match
  `bia_foia_logs_january_2026.pdf`. That one word boundary dropped **all 48
  Indian Affairs logs** while printing "0 foia-log links" — a matcher that
  fails closed and reports a zero looks exactly like a finding about the agency.
- **`InvalidURL` is not an edge block.** IHS publishes
  `.../FOIA Log FY 2026 Quarter 1.xlsx` with real spaces. `urllib` raises in
  0.02s, which is the same signature the shared fetcher reads as an IP-level
  refusal — so the first run reported "www.ihs.gov REFUSED" and skipped the
  agency. Percent-encode the path; an InvalidURL is a fact about OUR string.
- **A 403 is NOT a NOT_FOUND.** `hhs.gov`, `usda.gov` and `transportation.gov`
  answer 403 to a full browser header set on **every** path tried. Those
  agencies are `NOT_CHECKED`. Recording them as NOT_FOUND manufactures a
  coverage claim out of a block.
- **`hud.gov` lists its quarterly logs on a page that returns 200 and then
  refuses the log objects themselves.** Published ≠ retrievable.
- **A PDF with zero characters is a scan.** Interior's Office of the Secretary
  monthly logs from January 2026 are 14 pages, one image per page, and both
  pdfplumber and PyMuPDF return `""`.
- **Interior uses two control-number shapes.** Bureau logs use
  `DOI-2026-007831`; the Office of the Secretary uses `DOI-OS-2025-000123`. A
  pattern that matches only the first yields **zero rows and no error**.

### Reading a FOIA log PDF: the geometry, because there are no ruling lines

`extract_table()` returns `None` on every one of these files. Two methods that
look right and are not:

1. **x0 peak detection** — defeated by the description column, where 56 wrapped
   lines share one x while every other column has 11 rows.
2. **midpoints between header centres** — correct only for equal-width columns;
   it puts the boundary at x=271 when the description column starts at x=212.

What works: each header label is **centred** in its column and the header
banner rectangle carries the table's own edges, so `b[i+1] = 2*c[i] - b[i]`
walks the boundaries and **closure on the table's right edge is the check**.
Group the header **characters**, not words — several months emit their glyphs
scrambled (`Req D u a e t s e ted`), which destroys the label text but not the
x positions.

**And the two layouts align their cells in opposite directions.** The portrait
6-column bureau report is BOTTOM-aligned — the description block ENDS on the ID
line. The landscape 11-column Office of the Secretary report is TOP-aligned.
Get it backwards and every multi-line description is filed against the wrong
control number. An automatic detector was tried and abandoned (42 vs 1 on the
portrait report, but 382 vs 510 and 857 vs 686 on two landscape ones); the
layout itself is the reliable signal.

Where the geometry cannot be solved the file is **refused, kept and named**,
never parsed on a guess. Where a row survives with a description that begins
mid-sentence, it carries `parse_quality = SUSPECT_BOUNDARY` — the text is
verbatim, but its attribution to that control number is not established.


---

## An identifier is only as good as the row that carries it

**Measured 2026-08-12.** A resolution pass treated ANY EIN hit in
`cedar_identifier_ledger_final.csv` as tier A, on the reasoning that an EIN is an
exact identifier and needs no name heuristic. That reasoning is wrong.

    EIN rows in the ledger                                   1,104
    ...sitting on 52 entities that carry 5+ EINs each          873
    ...of those, tier B via `need_v6`                          821

`need_v6` is documented in `cedar_domain.ALGORITHMIC_METHODS` as **6.5% accurate
against rulings - never publishes alone**. The ledger was behaving correctly:
weak matches sat at B and did not publish.

**Promoting them on the consuming side laundered them.** Concretely it produced:

> UNITED WAY OF THE GREATER CHIPPEWA VALLEY, EIN 39-1077901, Wisconsin
> -> United Auburn Indian Community, California, **tier A**

alongside AMERICAN RED CROSS -> Holy Cross, AUBURN PUBLIC THEATER -> United
Auburn, and BOOKER T WASHINGTON COMMUNITY CENTER -> Washington Indian Gaming
Association.

**THE RULE: a tier is INHERITED from the source row, never assigned by the
consumer.** Only a method in `RULED_METHODS` earns A. An exact join on a weak
row is still a weak row - the exactness of the KEY says nothing about the
correctness of the LINK.

This is the same shape as the containment guard learned the same day: blocking
one path just pushes the bad match down to the next one. Here the bad match came
in through a path that looked authoritative *because* it was exact.

**Entities to watch** - 5+ EINs each, almost all `need_v6`: Onondaga 38,
Rosebud 38, Apache Tribe of Oklahoma 36, Cowlitz 35, Yavapai-Apache 34, Kiowa
Tribe 34, Pawnee Nation of Oklahoma 34, Tuscarora 33, Umatilla 32, Fort Mojave
31, Lenape Indian Tribe of Delaware 29, Coquille 28. A tribe with 38 EINs is a
matching artefact, not a corporate structure.

---

## CONCURRENCY RULES — earned 2026-08-26, from a near-loss

Ten-plus agents ran against this repo simultaneously on 2026-08-26. Everything
below is a rule paid for by an actual incident that day. Full write-up:
`review/_INCIDENT_2026-08-26_script163_number_collision.md`.

**1. A backup tag names the SCRIPT, not the number.**
Four agents each wrote a different `code/163_*.py` and each backed up as
`.bak_2026-08-26_pre163`. Correct form: `.bak_<date>_pre_<full_script_name>`.

**2. NEVER restore by glob.**
An agent restoring its own run with `*.bak_2026-08-26_pre163` reverted seven
files belonging to two other agents — dropping `cedar_identifier_ledger_final`
from 20,577 to 20,559 while the spine still carried the 179 NHOs those rows
belonged to. Restore by exact filename, always.

**3. Claim a script number BELOW the frontier, and verify it is free first.**
The frontier moved 158 → 171 in one hour. `ls code/` before you claim. The
numeric prefix has not implied step order since 2026-08-07 and there are now
38+ collisions.

**4. Verify the file you wrote by RE-READING it, not by trusting your run log.**
Two outputs reverted between runs on a shared machine. Idempotence is not
enough when someone else is writing.

**5. A full-rebuild stage and an in-place enricher on one file need an
ordering, and the ENRICHER RUNS LAST.**
`133 build` rebuilt `ferc_docket_filings.csv` four minutes after `168` wrote 931
entity links and nine columns into it, discarding all of them — and printed a
LARGER row count, which read as progress. Same shape as `09` reverting `50`.
A `.bak_*_pre<script>` file beside an output is the signal that an enricher has
touched it.

**6. Check mtimes and running processes before writing a shared table.**
`Win32_Process` for a live puller; `logs/_HOSTLOCK_*.json` for a host.

**7. A per-unit time budget that truncates and then marks COMPLETE is a silent
ceiling.** Four FERC dockets were written at 2,300-3,200 of 3,555-4,847
documents because `PER_DOCKET_BUDGET_S = 240`, then marked `done`, so no resume
would ever revisit them. Only comparing `documents_retrieved` against
`total_hits_reported_by_source` exposed it. Compare retrieved-vs-reported
wherever a source states a total.

**8. An absent column name reads as an empty source.** `102` counted two
datasets on a `tribe_id` column neither file has (both key `tribe_entity_id`)
and printed 0.0% coverage for 19 days while they held 307 and 274 keyed rows.
A coverage computation must RAISE on a missing column, never print a zero.

---

## THE GATE IS LOAD-BEARING. A FAIL IS NOT TO BE STEPPED AROUND. (2026-08-26)

`code/62_no_regression_check.py` failed on one line —
`codebook_undocumented_public = 45, must be 0` — for long enough that **six
separate agent sessions recorded it as "pre-existing, not mine" and moved on.**

That is the worst possible state for a gate, and it is worse than having no
gate at all. Not because the 45 mattered much, but because **a red gate that is
always red reports nothing.** Every other regression it could have raised in
those sessions was invisible behind a line everybody had learned to scroll
past. The gate had become a decoration.

It is green as of 2026-08-26 and it now carries teeth on shipping, on rebuild
reverts, on truncated collections and on absent coverage columns.

### The rule

**A FAIL from `62` is stop-work.** "Pre-existing, not mine" is not a
disposition. There are exactly three acceptable responses:

1. **Fix it.** Most failures here are cheap and local — register a codebook
   block, re-run the enricher, clear a `done` flag.
2. **Show it is not a defect**, change the check, and say in the script's own
   docstring why the old check was wrong. A metric removed without a written
   reason is a metric someone will re-add.
3. **If it genuinely belongs to another live agent**, name it HERE — the
   failing metric, the owning file or script, and what has to happen — before
   you continue. A named failure with an owner gets fixed. An unnamed one gets
   inherited.

Never re-baseline to make a failure disappear. `--baseline` records a floor; it
is not an acknowledgement button.

### What it now measures beyond the ledger and spine

| metric | shape | why |
|---|---|---|
| `ship_dist_rows`, `ship_tables_shipping` | must not FALL | shipping can only shrink if work was un-shipped |
| `ship_ratio_pct` | falls two ways, treated differently | see below |
| `ship_tables_at_zero`, `tables_missing_codebook_block`, `tables_missing_from_25_TABLES`, `tables_missing_from_27_SPEC`, `tables_missing_notes_contract` | must not RISE | these rise when a table lands in `data/clean` and nobody registers it |
| `files_with_columns_lost_vs_backup` | must be 0 | a full rebuild reverting an in-place enricher |
| `units_short_of_source_reported_total` | must be 0 | a per-unit budget that truncated and then marked `done` |
| `coverage_columns_that_do_not_exist` | must be 0 | a coverage count aimed at a column that is not there |
| `rulings_unapplied` | must not RISE | a ruling not written back to source is a note, not a ruling |

**`ship_ratio_pct` deliberately fails only when the SHELF SHRANK, not when the
WAREHOUSE GREW.** If the ratio falls while `ship_dist_rows` holds or rises, new
rows simply landed and have not shipped yet — that is collection doing its job,
and it prints as a loud named warning with the biggest unshipped tables listed.
If the ratio falls *and* shipped rows fall, that is lost shipping and it is a
hard fail. Failing the first case would punish collection and teach the next
agent to step around this gate, which is how we got here.

The registries are **imported from `160_ship_gap_report.py`** and the coverage
column list from `102_build_coverage_profile.py` — standing rule 8 applied to a
detector. `62` does not read `docs/SHIP_GAP_REPORT.json`: a guard that reads a
stale artefact certifies the defect, which this file already learned once at
the Kootenai invariant.

### Baselines recorded 2026-08-26

`ship_ratio_pct` **65.202%** · `ship_dist_rows` **5,227,896** of
**8,018,053** · `ship_tables_shipping` **49** of **257** ·
`ship_tables_at_zero` **205** · missing from `27_SPEC` **249**, from
`25_TABLES` **234**, no notes contract **206**, no codebook block **144** ·
`rulings_unapplied` **1,215** · the three trap metrics all **0**.

The baseline now also stores a **per-table `dist` row count for all 257
tables**. That is what lets the next run tell *"this specific table stopped
shipping"* from *"the total moved"*, which a scalar never could.

### A fourth rebuild/in-place collision, found by the new check on its first run

The retrieved-vs-reported check failed immediately on four FERC dockets —
P-2232 at 2,308 of 4,838, P-2146 at 2,404 of 4,847, P-1971 at 3,004 of 4,241,
P-2082 at 3,200 of 3,555 — the exact four `START_HERE.md` records as **topped
up earlier the same day**. The raw sheets agreed they had been: all 307 under
`data/raw/advocacy/ferc/docket_sheets/` complete, 0 short. The clean table was
not.

From the backups: `133 build` wrote the correct **307-docket** table at 17:37;
by 17:50 the live file was the **183-row pre-rebuild vintage** again with its
2026-08-12 truncated counts, and `168` then enriched *that*, adding its ten
entity-link columns to the stale table. `ferc_docket_filings.csv` did **not**
revert — it kept the rebuild *and* the links. **So the two files described
different universes: 102,615 filings drawn from 307 dockets, described by a
docket table listing 183.** Nothing printed a number that would have shown it.

Repaired by `code/175_restore_ferc_docket_table_after_rebuild_revert.py`:
307-row base + the ten enrichment columns merged on `(docket_number,
subdocket)`, verified first that the base contains every live key so nothing
could be dropped. **124 dockets recovered; the truncation metric went 4 → 0.**
The 124 recovered dockets carry **blank** entity-link columns — blank means
*not yet linked*, not *no link exists* — and re-running
`168_link_adjudication_hubs.py` (no network calls, honours every existing link)
fills them.

**The generalisation, now on the third and fourth instance: a partial restore
is a rebuild revert wearing a different hat.** Restoring one file of a set to a
pre-rebuild vintage while its siblings stay post-rebuild leaves the set
mutually inconsistent, and no single file looks wrong. Restore the set or none
of it, and re-run the enricher last.

---

## NAMED GATE FAILURE — not mine, owner identified (2026-09-02, GRAIN-LEGISLATION)

Per standing rule 15 option 3. `62_no_regression_check.py` exits 1 on
**fourteen** metrics. This workstream's changes are the `legislation` dataset:
`bill_votes.csv` enriched in place by `code/890_bill_votes_threshold_and_titles.py`
(60 → 68 columns, 423 → 423 rows) and `congressional_correspondence_log.csv`
ruled out of scope. **Not one of the fourteen traces to either**, and each was
checked individually rather than assumed:

| failing metric | why it is not this workstream's |
|---|---|
| `files_with_columns_lost_vs_backup` = 2 | named: `entity_evidence_profile.csv` (`.bak_2026-08-28_pre505`, 3 columns) and `federal_funding_tribe_year_panel.csv` (`.bak_2026-09-01_pre843`, `tribe_id` + `tribe_id_scheme`). Owners: the identity pass (505) and grain-ws4/843. `bill_votes.csv` vs its own `.bak_2026-09-02_pre890` **gained 8 and lost 0** |
| `tables_undocumented_in_codebook` = 16 · `tables_missing_codebook_block` = 16 | the 17 undocumented tables are constellation (`cedar_constellation_*`), geography (`geo_*`), `tribal_newsletter_*`, `native_business_*`, `consultation_*`, `wa_machine_transfers`, `gaming_property_locations`, `cedar_entity_freshness`. Owners: constellation 85x, geography 87x, and the gaming/nonprofit streams. 890 **added** 8 documented variables; `bill_votes.csv` matches `10_bills_votes` at **1.000** |
| `lint_new_defect_instances` · `lint_class2c` · `lint_class4` · `lint_class7` · `lint_bug_class_instances` | 293's new-instance list names `873_build_aiannh_crosswalk.py`, `900_nr_hub_join.py`, `950_promote_contract_attributes.py`, `870_build_geo_crosswalks.py`, `871_promote_geo_keys_contracts.py`, `962_probe_dear_tribal_leader_letters.py`, `518_dataset_readiness.py`/`621`. Owners: geography 87x, natural-resources 9xx, contracts 95x |
| `contract_violations` = 12 · `contract_orphan_shippable` = 7 | 512 names them: `federal_funding_transactions.csv`, `federal_funding_tribe_year_panel.csv`, `entity_aliases.csv`, and orphans `native_owned_businesses*.csv`, `nonprofit_schedule_c_*.csv`, `regulations_gov_*.csv`, `sam_native_class_distributions.csv`. **Zero legislation tables** — all 11 shippable legislation tables validate |
| `rulings_unapplied` 1,215 → 2,894 | no ruling layer was touched here |
| SHIPPING LOST `advocacy_passthrough_2026-08-07.csv` | lobbying/grain-ws3 — the table it names was ruled a duplicate vintage in `INTERNAL_TABLES` |
| STOPPED SHIPPING `hearing_bill_links.csv` 465 → 464 and `native_bills_subject_sweep.csv` 2,414 → 2,409 | **these two ARE legislation-adjacent and are still not this workstream's.** Both are the UPSTREAM workstream's deliberate 2026-09-01 de-dupe, recorded in `512.GRAIN_UPSTREAM` with the reason: the Congress.gov payload for event 338549 lists 27 of its 64 `relatedItems.bills` twice, and `all_bill_intros.csv` repeats 595 `bill_id`s byte-identically. Both were deduped **at ingest**, and 512 records "ZERO bill_ids leaving the table". Owner: UPSTREAM. **Worth a second look by that owner anyway** — standing rule 11 says un-shipped is a regression, and a row leaving the shelf as a side effect of a correctness fix still needs the shelf metric moved deliberately, not silently |

**One class-6 instance IS this workstream's and it was handled, not stepped
around.** Declaring the true `14 → 73 → 890` ordering in
`cedar_pipeline.KNOWN_ORDERINGS` made 293 see the collision it had been blind
to. It carries a `# lint-ok: class6` waiver on `14_build_bills_votes.py` with
the reason, which is the mechanism AGENTS.md asks for — the ordering written
down by a person, plus something that checks the columns survived
(`890 verify` exits 1 the moment one of its eight is missing).
`lint_class6` is **25**, below its baseline of 29.

---

## NAMED GATE FAILURE — not mine, owner identified (2026-08-28, ~18:20)

Per standing rule 15 option 3, recorded **before** the FY2021 subaward
promotion continued. `62_no_regression_check.py` exits 1 on **four** metrics.
All four were measured on a gate run started at **14:16:20 local, before this
session wrote a single byte to `data/clean/`**, so none of them is this
session's. Both causes are named below with their owning scripts.

| failing metric | baseline → measured |
|---|---|
| `lint_new_defect_instances` | 0 → **1** |
| `lint_class6` | 33 → **34** |
| `tables_missing_from_25_TABLES` | 234 → **235** |
| `tables_missing_from_27_SPEC` | 249 → **250** |

**Cause 1 — `lint_new_defect_instances` / `lint_class6`. Owner:
`code/97_build_aliases_and_relationships.py` → `entity_aliases.csv`.** The gate
names it itself: `NEW class6 instance: 97_build_aliases_and_relationships.py -
entity_aliases.csv`. Class 6 is *a full rebuild silently reverting an in-place
enricher*. 97 is a full-rebuild writer (`write_csv(CLEAN /
"entity_aliases.csv", …)`, line 1131) on a table that also has an in-place
enricher — the same rebuild/enricher pairing this file has already paid for at
`133`/`168`, `09`/`50` and the four FERC dockets. **What has to happen:** that
agent gives the pair an explicit ordering with **the enricher last**, or waives
the line with `# lint-ok: class6 - why`. Do NOT re-record 293's baseline.

**Cause 2 — the two registration metrics. Owner:
`code/417_build_entity_identity_crosswalk.py`, registered by
`code/419_register_identity_layer_codebooks.py`.** The single unregistered
table is **`cedar_entity_identity_crosswalk.csv`**, written **2026-08-26
21:02** — the Cedar ID system work that `docs/HANDOFF.md` lists as killed
mid-flight. Measured directly against the registries 62 imports:
`in 25_TABLES = False`, `in 27_SPEC = False`. It is only *partly* registered —
its codebook fragment (`data/clean/codebook/00d_cedar_entity_identity_
crosswalk.csv`) and its `dist/` notes contract both exist, which is why
`tables_missing_codebook_block` and `tables_missing_notes_contract` did **not**
rise. **What has to happen:** re-run the full 7-step ship chain (`py -3 code/build.py ship`; “87 → 25 → 27” is a 3-step shorthand that omits the codebook build, the gate, the coverage profile and the harmonised views) per
`docs/SHIPPING_RUNBOOK.md`; the codebook step is already done. That is the
shipping chain, which `HANDOFF.md` says to run in a quiet window, and it
rewrites shared `dist/` artefacts — so it is deliberately NOT run from inside
the subaward promotion.

*(A second table, `cedar_correction_register.csv`, also landed after the
baseline snapshot and is fully registered in both registries. It is not part of
this failure and is named only so the next agent does not re-derive it.)*

**Why this is safely separable from the subaward work.** The three trap metrics
— `files_with_columns_lost_vs_backup`, `units_short_of_source_reported_total`,
`coverage_columns_that_do_not_exist` — are all **0**, and `ship_dist_rows` rose
7,444,230 → 8,463,001. Nothing is lost; both causes are registration/lint gaps
on tables the subaward promotion does not touch. `subawards.csv` is in neither
cause. The promotion proceeded against this named failure and touched none of
`entity_aliases.csv`, `cedar_entity_identity_crosswalk.csv`, 25_TABLES or
27_SPEC.

**Also emitted, and it is benign:** `[ordering hazard] subawards.csv is older
than its own backup subawards.csv.bak_2026-08-28_pre_121_pull_subawards_api`.
That is this session's own pre-write backup, taken minutes before the gate ran
and before `append` rewrote the table. It clears itself the moment the table is
written. A `.bak` newer than its table means a backup was taken and the write
has not happened *yet* — it is not evidence of a revert.

## NAMED GATE FAILURE — not mine, owner identified (2026-08-26, ~18:30)

Per standing rule 15 option 3. `62_no_regression_check.py` FAILS on four
metrics, all caused by the same four tables and all rising by exactly 4:

| failing metric | 205/234/249/206 → | 209/238/253/210 |
|---|---|---|
| `ship_tables_at_zero` | 205 | **209** |
| `tables_missing_from_25_TABLES` | 234 | **238** |
| `tables_missing_from_27_SPEC` | 249 | **253** |
| `tables_missing_notes_contract` | 206 | **210** |

**Owner: the lobbying-registrant agent.** The four unregistered tables are
`lobbying_registrant_client_relationships.csv` (1,309),
`lobbying_registrants.csv` (653), `lobbying_registrant_identifiers.csv` (525),
`lobbying_registrant_concentration.csv` (36), written by
`code/180_build_lobbying_registrant_hub.py` (18:16) and
`code/181_enrich_lobbying_registrant_identifiers.py` (18:20).
**`181` was still RUNNING as PID 25336 at 18:21** — this is live work, not
abandoned work, and registering another agent's in-flight tables would race it.

**What has to happen:** that agent registers a codebook block for its four
tables, then re-runs the full 7-step ship chain (`py -3 code/build.py ship`; “87 → 25 → 27” is a 3-step shorthand that omits the codebook build, the gate, the coverage profile and the harmonised views) per `docs/SHIPPING_RUNBOOK.md`. The three
trap metrics (`files_with_columns_lost_vs_backup`,
`units_short_of_source_reported_total`, `coverage_columns_that_do_not_exist`)
are all **0** and shipped rows did not fall, so nothing is lost — this is a
registration gap on brand-new tables, the exact "warehouse grew, shelf did not"
case the gate is designed to distinguish.

The ANCSA ruling work of 2026-08-26 (`code/191_*` … `code/194_*`) proceeded
against this named failure and touched none of these four tables.

**RESOLVED the same evening, by its owner, exactly as the rule intends.** The
re-run of `62` after the ANCSA work returned **exit 0, "no regressions"**:
`ship_tables_at_zero` 209 → **205**, `tables_missing_from_25_TABLES` 238 →
**234**, `tables_missing_from_27_SPEC` 253 → **249**,
`tables_missing_notes_contract` 210 → **206** — each back to its baseline, all
four by exactly the 4 tables named above, and `tables_missing_codebook_block`
additionally fell 144 → **140**.

**This is the first time the naming rule has been exercised end to end, and it
worked in about an hour.** The failure was named with its owner instead of
being recorded as "pre-existing, not mine", the owning agent registered its
blocks, and the gate went green without anyone re-baselining or stepping
around it. Contrast the six sessions that inherited an unnamed failure and hid
every other regression behind it. **A named failure with an owner gets fixed;
that is now measured, not asserted.**

## NAMED GATE FAILURE — not mine, owner identified (2026-08-26, ~20:10)

Per standing rule 15 option 3, by the **harmonisation agent** (`code/334`–`337`,
the assistance seam and period-column work). `62_no_regression_check.py` FAILS
on five metrics, all caused by **one** new table and all rising by exactly 1:

| failing metric | before → after |
|---|---|
| `ship_tables_at_zero` | 138 → **139** |
| `tables_missing_codebook_block` | 139 → **140** |
| `tables_missing_from_25_TABLES` | 234 → **235** |
| `tables_missing_from_27_SPEC` | 249 → **250** |
| `tables_missing_notes_contract` | 139 → **140** |

**Owner: the lobbying-attribution-withdrawal agent** (`code/350`–`354`). The
unregistered table is **`data/clean/cedar_correction_register.csv`** (18 rows,
written 20:08), by `code/350_withdraw_false_lobbying_attributions.py` and
`code/354_correction_register.py`, with
`code/351_rebuild_lobbying_panel_from_corrected_disclosures.py` in the same
family. It is a genuinely useful table — it records withdrawn false
attributions with the provenance preserved (e.g. *Santa Rosa County, Florida*
unlinked from `TRBF-SROSAR-00`, matched on the token pair "rosa santa").

**It is not mine and it is not in my claimed number range** (334–341). The
gate's three trap metrics — `files_with_columns_lost_vs_backup`,
`units_short_of_source_reported_total` and
`coverage_columns_that_do_not_exist` — are all **0**, and shipped rows did not
fall (7,444,230 → 7,444,230). This is the "warehouse grew, shelf did not"
registration gap the gate is built to distinguish, not a loss.

**What has to happen:** that agent registers a codebook block for
`cedar_correction_register.csv`, then re-runs 25 → 27 per
`docs/SHIPPING_RUNBOOK.md`. (**87 has already been re-run** — see below — so
only 25 and 27 remain.)

**A SIXTH failure appeared at 20:20 and belongs to the same owner:**

> `!! A TABLE THAT WAS SHIPPING STOPPED SHIPPING — tribe_year_lobbying_panel.csv:
> 5,051 → 4,997`

That is **−54 rows, and it matches to the row** an earlier `ship_dist_rows` dip
of 7,444,230 → 7,444,176 seen at 20:14. The cause is
`code/351_rebuild_lobbying_panel_from_corrected_disclosures.py` rebuilding the
panel after `350` withdrew the false attributions recorded in
`cedar_correction_register.csv`. **This one is almost certainly CORRECT work —
withdrawing Santa Rosa County, Florida from a California tribe SHOULD reduce
the panel** — but standing rule 11 makes any un-shipping a regression that must
be stated rather than absorbed, and the owning agent is the one that can say so
with the evidence. It needs an explicit note that the fall is intended, not a
re-baseline.

**87 was re-run by the harmonisation agent at 20:18**, deliberately, because
the `vintage` fix it carries is the point of that work: `ship_dist_rows` rose
7,444,230 → **7,445,042** and the ship rate reached **100.0%** (7,445,042 of
7,445,042 rows reaching a notes contract). That run is additive and reads only
clean tables, so it does not race `350`/`351`; it does mean the notes contract
now reflects the corrected panel.

The harmonisation work of 2026-08-26 (`code/334`–`337`) proceeded against this
named failure and **touched none of the lobbying tables**. Its own gate
movement was in the improving direction only: `lint_bug_class_instances`
182 → 168, `lint_class6` 33 → 32, `lint_class7` 74 → 61, and
`coverage_columns_that_do_not_exist` held at 0 while the declared pair count
rose 22 → 23.


---

## NAMED GATE FAILURE — five shipping metrics, owner identified (2026-08-26 18:27)

Named here per standing rule 3 (*"if it genuinely belongs to another live agent,
name it HERE — the failing metric, the owning file or script, and what has to
happen — before you continue"*), by the agent that built
`code/186_cicd_benchmark.py`. **186 writes nothing to `data/clean` and cannot
have caused this**; it writes only `docs/CICD_BENCHMARK.md` and
`docs/cicd_benchmark.json`.

`code/62_no_regression_check.py` FAILS on five metrics, all with one cause:

```
ship_tables_at_zero            205 -> 210
tables_missing_codebook_block  144 -> 145
tables_missing_from_25_TABLES  234 -> 239
tables_missing_from_27_SPEC    249 -> 254
tables_missing_notes_contract  206 -> 211
```

**Cause: five lobbying-registrant tables landed in `data/clean` unregistered,
between 18:16 and 18:26 today — while 62 was running.**

| table | rows | mtime |
|---|---:|---|
| `lobbying_registrant_client_relationships.csv` | 1,309 | 18:16:59 |
| `lobbying_registrant_concentration.csv` | 36 | 18:16:59 |
| `lobbying_registrant_identifiers.csv` | 525 | 18:21:29 |
| `lobbying_registrant_native_ownership_evidence.csv` | 27 | 18:26:30 |
| `lobbying_registrants.csv` | 653 | 18:26:30 |

**OWNER: whoever is running `code/180_build_lobbying_registrant_hub.py`,
`code/181_enrich_lobbying_registrant_identifiers.py` and
`code/182_rule_lobbying_registrant_native_ownership.py`.** Those three scripts
are the only ones in `code/` that write these names, and the mtimes say that
agent was still mid-run at the moment the gate ran — this is unfinished work,
not abandoned work.

**WHAT HAS TO HAPPEN:** register a codebook block for each of the five, then
re-run `the full 7-step ship chain (`py -3 code/build.py ship`; “87 → 25 → 27” is a 3-step shorthand that omits the codebook build, the gate, the coverage profile and the harmonised views)` per `docs/SHIPPING_RUNBOOK.md`. **Do not run
`41_build_codebooks.py`** to do it — it is a global rebuild and
`docs/INDIVIDUAL_NATIVE_OWNERSHIP_VERIFICATION_BUILD_LOG.md` §10 records that it
would delete 21 of the 43 blocks the master now holds. Use a fragment +
`cedar_register_codebook.py`, the pattern
`156_refresh_deals_codebook_fragment.py` set.

The three trap metrics (`files_with_columns_lost_vs_backup`,
`units_short_of_source_reported_total`, `coverage_columns_that_do_not_exist`)
are all **0**, and `ship_dist_rows` held at 5,227,896 — so nothing was lost.
This is collection outrunning registration, which is the case
`ship_ratio_pct` is deliberately built not to punish. It is still a FAIL on the
five counters above and it is still stop-work for whoever owns those scripts.


---

## NAMED GATE FAILURE — four shipping metrics, owner identified (2026-08-26 19:00)

Named per standing rule 3 by the agent claiming script numbers **284–292**
(database-integration layer: `code/cedar_keys.py`, `code/cedar_schema.py`,
`code/284`–`code/289`, `docs/DATABASE_INTEGRATION.md`). **That work writes
nothing to `data/clean` and cannot have caused this** — it writes only
`code/`, `docs/`, `docs/schema/` and `dist/collections/`.

`code/62_no_regression_check.py` FAILS on four metrics, one cause:

```
ship_tables_at_zero            205 -> 207
tables_missing_from_25_TABLES  234 -> 236
tables_missing_from_27_SPEC    249 -> 251
tables_missing_notes_contract  206 -> 208
```

All four rise by exactly **2**, and 62 names the two tables itself:

| table | rows | clean mtime | producing script | script mtime |
|---|---:|---|---|---|
| `contractor_ranking.csv` | 1,429 | 19:00:09 | `code/269_build_contractor_ranking.py` | 18:59:48 |
| `individual_native_firm_register.csv` | 45 | 18:59:02 | `code/241_promote_individual_native_firms_in_place.py` | 18:58:38 |

**OWNERS: whoever is running `code/269_build_contractor_ranking.py` and
`code/241_promote_individual_native_firms_in_place.py`.** Both scripts were
written to disk *within ninety seconds of the gate run* and both output files
are newer than the scripts — this is live work, not abandoned work, and
registering another agent's in-flight tables would race it.

**WHAT HAS TO HAPPEN:** each owner registers a codebook fragment for its table
(`cedar_register_codebook.py`, or the pattern in
`156_refresh_deals_codebook_fragment.py`), then re-runs `the full 7-step ship chain (`py -3 code/build.py ship`; “87 → 25 → 27” is a 3-step shorthand that omits the codebook build, the gate, the coverage profile and the harmonised views)` per
`docs/SHIPPING_RUNBOOK.md`. **Do not run `41_build_codebooks.py`.**

The three trap metrics (`files_with_columns_lost_vs_backup`,
`units_short_of_source_reported_total`, `coverage_columns_that_do_not_exist`)
are all **0** and `ship_dist_rows` ROSE 5,227,896 -> 5,230,446, so nothing is
lost. This is the "warehouse grew, shelf did not" case the ratio metric is
deliberately built not to punish. It is still a FAIL on the four counters and
still stop-work for those two owners.

**Note for the register's owner: `individual_native_firm_register.csv` is
additionally blocked on a key question, not just a registration one.** See
`docs/DATABASE_INTEGRATION.md` — an individually Native-owned firm must not be
keyed by a UEI that resolves to a natural person's name, and
`verification_id = INV-{rank:04d}` is rank-derived (the defect
`171_build_individual_native_verification.py` already records at line 338).

---

## A BUILD THAT READS THE ADDITIONS MUST ALSO READ THE LEDGER (2026-08-26)

**And a build must STATE which file it treats as the truth.**

This is the fifth write-up of one defect and the first one that is enforced by
code rather than by prose, because prose demonstrably did not work.

### The defect

    glob("data/clean/deals_*_additions.csv")

reads the ADDITIONS to the deals ledger and never the **LEDGER ITSELF**. That
is why a 790-row deals master held exactly **one** row dated 2026 while 131
verified rows sat in two CSVs in the project root.

`docs/FACT_CHECK_2026-08-06.md` finding **B-1** named this miscount on
2026-08-06, in as many words: *"the audit globs `deals_*_additions.csv` and
never sees the 132 rows in the root ledgers."* **It was still live in eight
scripts twenty days later.**

### WHY IT SURVIVED THREE REPAIRS, WHICH IS THE PART WORTH LEARNING

`88_build_deals_taxonomy.py`, `57_autoresolve_deal_parties.py` and
`41_build_codebooks.py` were each fixed by the session that happened to trip
over them, and each session recorded the fix as complete. **Nobody enumerated
the instances.** Script `53_apply_agent_deals_rulings.py` even carried a comment
naming the defect in script 33 - *"Script 33 counts only `deals_*_additions.csv`
and so undercounts by the 132 rows in the two root ledgers"* - and 33 went on
carrying it for three more weeks. **Naming a defect in a neighbour's comment is
not fixing it.**

Measured 2026-08-26, the eight that were still carrying it:

| script | what it got wrong |
|---|---|
| `82_build_gaming_property_dataset.py` | `n_deals_for_entity` in the **SHIPPING** view |
| `35_coverage_audit.py` | wrote **deals = 790** into `data/clean/coverage_audit.csv`, the file prioritisation reads |
| `33_apply_party_rulings.py` | a coverage **denominator** - omitting rows OVERSTATES coverage, the direction that stops anyone looking |
| `59_build_deal_source_index.py` | 145 rows contributed no source URL to the source index |
| `73_add_tcu_and_cdfi.py` | candidate discovery - a party never offered reads as "no evidence" |
| `31_build_dataset5_linked.py` | a hand-written list of **3 of 9** additions files, so 216 of 935 rows fed `ownership_events.csv` |
| `24_generate_dataset_docs.py` | told a reader the dataset **is** three additions files |
| `175_sync_published_property_view_entities.py` | copied 82 verbatim, on purpose, and said so |

### THE RULE

1. **A build that reads the ADDITIONS must also read the LEDGER.**
2. **A build must STATE which file it treats as the truth** - in its docstring,
   by name, at the top.

Operationally: a **CONSUMER** (counting, joining, auditing, profiling,
documenting) reads the **PROMOTED TABLE** and nothing else. Only a **PRODUCER**
whose job is to *build* the promoted table reads the parts, and it must read
**every** part.

### AND A SECOND REASON, WHICH THE FIRST FIX MISSED

Assembling the parts by hand is not good enough either, even when you get all
of them. Measured:

    9 x deals_*_additions.csv                        790
    deals_2026_ytd.csv                                90
    deals_historical_2020_2025.csv                    56
    union of distinct Deal_ID                        936
    data/clean/deals_classified.csv  (THE TRUTH)     935

The parts union to **936** and the truth is **935**. `54_reconcile_deals_duplicates.py`
deliberately leaves a withdrawn row in its source file, so every consumer that
assembles the universe itself must also re-implement
`review/deals_withdrawn_duplicates.csv` - and `32`, `53`, `57`, `91` and `100`
all read the ledgers *and* the additions and **none of them did**, so a
withdrawn duplicate (`MA2020-008`, the Calista/Nordic row) stayed live in five
places. **The promoted table already honours the withdrawal. That is the second
reason a consumer must never assemble the universe itself.**

### DECLARED IN ONE PLACE

`cedar_domain.PROMOTED_TABLES` maps a promoted table to its parts;
`cedar_domain.PROMOTED_TABLE_PRODUCERS` names the builds allowed to read the
parts, each with its reason; `cedar_domain.DEALS_TRUTH` is the deals answer.
Add a family the day it is created, not the day it is miscounted.

### AND IT IS NOW CHECKED - `160_ship_gap_report.py` section 3(h)

Section 3(g) of that script already reported *"7,009 rows in 8 root CSVs no
registry enumerates"* and said, correctly, that this is *"the shape of the deals
defect."* **That is the symptom. Section 3(h) is the cause, and it is
checkable.** `promoted_table_part_readers()` scans every `code/**/*.py` and
names every script that reads a PART without reading the promoted table - a
`READS_PARTS_NOT_PROMOTED_TABLE` gap in `docs/SHIP_GAP_REPORT.json` carrying
the offending filename, the parts it read, and the fix.

It is a **text** scan, not `ast`, deliberately: the part names appear as glob
patterns, f-string fragments and hand-written lists, and an `ast` literal walk
missed two of the eight. A false positive costs a reader ten seconds; a false
negative costs three weeks in a shipping artefact.

**Baseline 2026-08-26: `builds_reading_parts_not_promoted_table` = 0**, over 11
declared producers and 16 consumers. It was 8 before this pass.

**The generalisation for the root CSVs:** 3(g) lists eight root files holding
7,009 rows that no registry sees. Two of them are the deals ledgers, and the
promoted-table declaration now covers those. **The other six -
`entity_master.csv` (815), `entity_crosswalk_bgov.csv` (752),
`reconcile_queue.csv` (326), `bgov.csv` (878), `contract-03-18-*.csv` (4,000),
`Assistance_56G180126_*.csv` (92) - are the same defect awaiting its promoted
table.** Each needs a declared truth in `PROMOTED_TABLES`, or a written ruling
that it is raw input and not a dataset. Until one or the other, 3(g) is an
inventory of work nobody owns.

---

## THE `n_deals_for_entity` FIX: PREFER A JOIN KEY OVER A CLEVERER STRING MATCH

The second defect in `82_build_gaming_property_dataset.py` was worse than the
glob, and is the more useful lesson.

    deals[sp["canonical_name"].lower()]   vs   Native_Party.lower()

A **short spine canonical name** matched **exactly** against a **free-text party
string**. So *"Saint Regis"* never matched *"saint regis mohawk tribe"*,
*"Mashantucket Pequot"* never matched *"mashantucket pequot tribal nation"*, and
*"The Chickasaw Nation"* never matched any of its **22** ruled deal rows.

**The obvious fix - loosen the comparison to containment or token overlap - is
the containment defect, which has failed TEN distinct ways in this file
already.** `CHICKASAW NATION` to *Chickasaw Children's Village* put $2.8B on a
school. `NATIVE VILLAGE OF ELIM` to *Elim Native Corporation*. A place suffix
makes a tribe name a place. Two guards built to save it were measured and
removed because they lost 130 and 582 correct rows.

**"Saint Regis" is contained in "saint regis mohawk tribe", which is precisely
the containment shape.** A fix that widens matching can be worse than the bug
it replaces.

**So no name is compared at all.** `deals_classified.csv` already carries
`native_party_entity_id`, written by `126_apply_deal_party_attribution.py` from
hand rulings, agent research and the autoresolver, **each row's tier inherited
from its source row**. That column IS a spine `tribe_id`; the property row
carries a `tribe_id`; the join is exact.

It also **inherits every refusal already ruled by hand**, which a looser string
match would have silently re-opened - including the four containment refusals in
`review/deals_party_refused_2026-08-26.csv` (Riverside San Bernardino County
Indian Health to "Native Health", **Arizona**; Department of Hawaiian Home Lands
to an NHO; and two **aggregate** party strings keyed to a single tribe).

**Measured on the live shipping view**
(`code/255_fix_gaming_property_deal_counts.py`, in place, one column, no
rebuild): 617 of 784 rows changed, **617 rose and 0 fell**, the column's sum
went **209 to 2,549**, and properties with at least one deal reached **646**.
886 of the 935 deal rows carry an entity id (94.8%); **the 49 that do not are
counted for no entity rather than guessed onto one.**

**Why an in-place patch and not a re-run of 82:** `gaming_properties.csv` has
three in-place enrichers (`158_merge_staged_labor_employment.py`,
`160_sync_published_gaming_view.py`, `175_sync_published_property_view_entities.py`)
and 82 is a full rebuild. Concurrency rule 5 - the enricher runs last - means a
rebuild here costs three re-runs and risks the exact `133`/`168` collision that
happened four times on 2026-08-26. **Repairing one column in place is the
smaller, checkable operation.** Schema is unchanged on purpose, so no codebook
block, notes contract or publication spec has to move.

### Scripts checked and found CLEAN in the same sweep, by name

Recorded because this project counts what it drops. Reading the parts *and* the
ledgers: `88`, `57`, `54`, `91`, `100`, `32`, `53`, `ancsa_portal/build_deals`,
`ancsa_v2/build_v2` (the last two are producers and stay on the parts).
Already reading the promoted table before this pass: `41_build_codebooks.py`,
`126_apply_deal_party_attribution.py`, `151_rebuild_entity_evidence_profile.py`,
`153`, `155`, `156`. Reading a party-attribution by-product rather than the
ledger, which is correct for their purpose: `08_build_review_page.py`,
`62_no_regression_check.py`, `70_key_unjoined_datasets.py`,
`129_build_review_queue.py`. `38_fain_backfill.py` and
`build_federal_award_rows.py` operate on ONE named additions file by design and
are declared producers.

---

## NAMED GATE FAILURE — four unregistered tables, owner identified (2026-08-26 ~19:05)

Named here per standing rule 15 option 3, by the agent that ran the
promoted-table sweep (`code/255_fix_gaming_property_deal_counts.py`, the
`cedar_domain.PROMOTED_TABLES` declaration and the `160` section 3(h) check).

**`62_no_regression_check.py` was GREEN when this pass started (18:30) and FAILS
on four metrics at 19:05.** Same cause on all four, and it is not this pass:

```
ship_tables_at_zero            205 -> 209
tables_missing_from_25_TABLES  234 -> 238
tables_missing_from_27_SPEC    249 -> 253
tables_missing_notes_contract  206 -> 210
```

**Cause: four tables landed in `data/clean` unregistered between 18:59 and
19:03 — while this pass was running.**

| table | mtime |
|---|---|
| `individual_native_firm_register.csv` | 18:59 |
| `individual_native_firm_contracts.csv` | 19:01 |
| `individual_native_firm_contracts_published.csv` | 19:01 |
| `contractor_ranking.csv` | 19:03 |

**OWNER: whoever is running `code/241_promote_individual_native_firms_in_place.py`,
`code/242_build_individual_native_firm_contracts.py`,
`code/243_write_individual_native_class_codebook_fragment.py` and
`code/269_build_contractor_ranking.py`.** Those are the only scripts in `code/`
that write these names. **None of the four existed when this pass listed
`code/` at 18:30** — the frontier was 234 then and 269 now — so this is live
work, not abandoned work.

**WHY IT IS NOT THIS PASS.** This pass wrote exactly two files in `data/clean`,
both already-registered tables, neither new:

* `gaming_properties.csv` — **one existing column rewritten in place**
  (`n_deals_for_entity`), schema deliberately unchanged, row count and column
  list asserted before writing and the file re-read from disk and verified
  after. `files_with_columns_lost_vs_backup` is **0**, which is the metric that
  would have caught it if it were wrong.
* `coverage_audit.csv` — regenerated by `35_coverage_audit.py`, same 6 columns.

The three trap metrics are all **0** (`files_with_columns_lost_vs_backup`,
`units_short_of_source_reported_total`, `coverage_columns_that_do_not_exist`)
and `ship_dist_rows` **rose** 5,227,896 -> 5,230,446. Nothing was lost. This is
collection outrunning registration — the case `ship_ratio_pct` is deliberately
built not to punish — and it is still a FAIL on the four counters above.

**WHAT HAS TO HAPPEN:** that agent registers a codebook block for each of the
four, then re-runs `the full 7-step ship chain (`py -3 code/build.py ship`; “87 → 25 → 27” is a 3-step shorthand that omits the codebook build, the gate, the coverage profile and the harmonised views)` per `docs/SHIPPING_RUNBOOK.md`. **Do not run
`41_build_codebooks.py`** to do it — it is a global rebuild and would delete 21
of the 43 blocks the master now holds. Use a fragment plus
`cedar_register_codebook.py`, the pattern `156_refresh_deals_codebook_fragment.py`
set. `code/243_write_individual_native_class_codebook_fragment.py` looks like it
is already that step for three of the four; `contractor_ranking.csv` has no
fragment writer in `code/` yet.

### CORROBORATED 19:12 by an independent pass, and two of the four have since cleared

The tier-integrity pass (`code/248`–`code/251`) re-ran `62` at 19:12 and
measured the same cause from a different starting baseline. Worth recording
because it shows the naming rule working a second time in one evening:

```
tables_missing_from_25_TABLES  234 -> 238   STILL FAILING
tables_missing_from_27_SPEC    249 -> 253   STILL FAILING
ship_tables_at_zero            205 -> 138   CLEARED (fell, hard)
tables_missing_notes_contract  206 -> 139   CLEARED (fell, hard)
```

So the owning agent's `243_write_individual_native_class_codebook_fragment.py`
step **is landing** — `ship_dist_rows` rose 5,227,896 -> **7,444,208** and
`ship_tables_shipping` 49 -> **125** in the same window. What remains is the
`25`/`27` registration half. The four tables are unchanged:
`individual_native_firm_register.csv` (45 rows),
`individual_native_firm_contracts.csv` (324),
`individual_native_firm_contracts_published.csv` (613),
`contractor_ranking.csv` (1,429, from `code/269_build_contractor_ranking.py`).

**The tier-integrity pass added NO table to `data/clean`.** It wrote two
existing files in place — `subawards.csv` (93 cells in two existing tier
columns) and `np_orgs.csv` (27 rows, existing columns only) — and everything
else went to `review/`. `files_with_columns_lost_vs_backup` is **0** on both.

---

## A RULED METHOD IS NOT A POSITIVE RULING (2026-08-26)

This file already carries *"a tier is INHERITED from the source row, never
assigned by the consumer"*, learned on the United Way case. **That sentence has
a second half, and its absence shipped a worse bug than the one it fixed.**

`code/148_resolve_schedule_i_recipients.py` quoted the rule correctly in a
comment and then wrote:

```python
RULED = {"hand", "bgov_manual", "elijah_ruling", ...}
tier = "A" if meth in RULED else (r.get("confidence_tier") or "B")
```

`attribution_method` says **WHO** decided. `confidence_tier` says **WHAT** was
decided. Measured on `cedar_identifier_ledger_final.csv`, 2026-08-26:

```
EIN rows                  1,104
...tier A                     0
...`elijah_ruling`          317      EVERY ONE TIER X - every one an EXCLUSION
```

That line turned **317 owner exclusions into publishable positive
attributions** — `COLVILLE ROTARY CHARITABLE FOUNDATION -> Confederated
Colville` at tier A, `KIOWA COUNTY FARM BUREAU -> Kiowa Tribe`, `COWLITZ COUNTY
DIVE RESCUE -> Cowlitz`, and 314 more. It is worse than the United Way case:
that one laundered a *weak* link, this one inverts the *sign* of a human ruling.
`docs/NONPROFIT_ENTITY_LINKAGE_BUILD_LOG.md` spotted it and reported the count
as 42; the ledger has grown and 317 is today's figure.

**The same trap, in a second vocabulary, on the same day.** The ANCSA pass read
`status = SETTLED` as confirmation on a ruling whose `outcome` was
`HOLD_OVER_OWNER` — *"HOLD — RETRACTION REQUIRED"*.

> **`status` says the ruling was PROCESSED. `outcome` says what it DECIDED.**

Method, status, authority, who-signed-it: all the same column in different
clothes, and **none of them carries a sign**.

### The rule

    A tier is INHERITED from the source row.
    A RULED method is not automatically a POSITIVE ruling.
    Before you inherit a ruling's AUTHORITY, read its OUTCOME.
    Demoting is safe; promoting is not.

And its corollary, learned when fixing 148: **an exclusion must block every
path, not the one it arrived on.** Refusing the EIN route alone just hands
`COLVILLE ROTARY -> Confederated Colville` back through the name resolver —
this file's own *"blocking one bad-match path pushes it to the next"*. It must
NOT become a blanket block on the identifier either: the ruling says this EIN
is not THAT entity, and over-blocking would suppress a correct attribution, the
reason `169_build_identifier_graph.py` makes corrections **repoint, not
blacklist**.

### The standing detector

**`code/293_lint_bug_classes.py` — and ONLY that one.**
`code/248_audit_tier_inheritance_patterns.py` was a second detector for this
same class, written the same evening by a different agent. **It is RETIRED as
of 2026-08-26**; its disposition table and its ledger-exposure measurement were
folded into 293 verbatim, and the file is now a stub that redirects and exits
non-zero. See "TWO DETECTORS FOR ONE CLASS" below. The description that follows
is of the folded-in behaviour, which is now reached with:

    py -3 code/293_lint_bug_classes.py --class 3

It scans `code/*.py` for a
tier assignment sitting beside a ruling-method test, checks each hit against a
recorded per-site disposition made by reading the code, **re-derives the ledger
exposure rather than quoting it**, and **exits non-zero on any site with no
recorded disposition**. A regex cannot decide these; storing the human decision
next to the scan means only novelty raises. Run it after touching any tier.

Result of the first full audit — 20 sites, 9 files:

| verdict | files |
|---|---|
| FIXED | `148_resolve_schedule_i_recipients.py` |
| CLEAN | `09`, `124`, `34`, `19`, `163_promote_nho_universe_in_place`, `70`, `91`, `173`, `174`, `169`, `172`, `147`, `167`, `25` |
| NOTED | `97_build_aliases_and_relationships.py` |
| LIVE (another agent) | `241_promote_individual_native_firms_in_place.py` |

**`163_promote_nho_universe_in_place.py` is the model to copy.** It reads the
sign explicitly — `if tier == "X": skip — source row is tier X (ruled NOT
NHO-owned)` — and then requires tier A on the **source** row before writing.

**~~`97_build_aliases_and_relationships.py` is NOTED, not clean~~ — FIXED
2026-08-26.** `if tier != Tier.A and not ruled: continue` admitted a row on
method membership alone and then minted an **`owned_by` edge at tier A** —
`owned_by` is in `OWNERSHIP_BEARING`, so it can carry money. It is *not* the
negative-ruling bug: `ledger_firms` filters `confidence_tier == X` out before
that loop, so no exclusion can reach it. Measured exposure: **36 rows** — 34
tier-B `elijah_ruling_redirect`, 2 tier-C `web_verified` (Kijik, Paskenta,
Paug-Vik, Sitnasuak, Tlingit & Haida). The **entity** is right on all 36; only
the tier is over-stated.

**The fix, in two halves, because 97 is a FULL REBUILD and
`entity_relationships.csv` has in-place consumers.**

1. **In the build.** The tier and its confidence are now INHERITED verbatim
   from the ledger row (`tier=tier, confidence=LEDGER_TIER_CONFIDENCE[tier]`,
   `verification_status="TIER_" + tier`), and the notes on every edge say which
   method the tier came from. The 0.90 confidence was the same over-statement
   in a second column and moved with the tier. `LEDGER_TIER_CONFIDENCE` is now
   one constant used by both sites in the file instead of two literals.
   The summary now reports `owned_by_inherited_tier` — a per-tier breakdown —
   because a single "owned: N" count is exactly what let 100% of these ship at
   A unnoticed.
   **Also fixed: the dedupe key is `(entity, normalised legal name)` and
   several ledger rows can share it** — CAGE `3BVB7` carries both a tier-B
   `elijah_ruling_redirect` and a tier-A `bgov_manual` row for *Executive
   Protection Systems LLC*. Taking whichever came first in FILE ORDER made the
   edge's tier depend on ledger row order; the loop is now sorted strongest
   tier first, which is still INHERITING — it never writes a tier no source row
   states.

2. **In the live file**, by `code/310_correct_overstated_owned_by_edge_tiers.py`
   — in place, demote-only, backup + `.part`-then-rename + re-read.

**AND HERE IS THE NUMBER THAT MATTERS, BECAUSE "36 LIVE ROWS" WAS NOT TRUE.**
36 is the **LEDGER exposure** — the rows a re-run of 97 would over-state today.
`entity_relationships.csv` was built 2026-08-07 and holds **1,462** `owned_by`
edges, so the two populations are not the same population:

| | n |
|---|--:|
| ledger rows a `ruled method → tier A` consumer would over-state | **36** |
| …that have a live `owned_by` edge at all | **5** |
| …of those 5, edges whose firm ALSO has a tier-A ledger row today (correctly A) | **3** |
| **live edges actually over-stated, and corrected** | **2** |
| ledger rows with no live edge — the ledger grew after 97 last ran | **31** |

The two corrected are `CEDAR-REL-00014391` (UEI `CJ6USAF6QF94`, *T&H Services
Llc* → Tlingit & Haida) and `CEDAR-REL-00014440` (UEI `V4GVJZF4S263`,
*Nakupuna Solutions, Llc* → Nā Kūpuna), both **tier A → C**, both
`web_verified`. The three that are correctly A are CAGE `3BVB7`, `8EGN7` and
`78PY0`: their edge `notes` carry the *tier-A row's* spelling of the legal
name, which is the evidence that the A row minted them. **Entity untouched on
all five.** The other 31 never reached the file, and the build fix is what
stops the next run minting them at A. Audit:
`review/overstated_owned_by_tier_corrections_2026-08-26.csv`.

**The rule this earns: an EXPOSURE COUNT IS NOT A ROW COUNT.** "36 rows" read
as "36 rows in the table" for the whole day it sat in this file. It was 36 rows
in the LEDGER, of which 2 were wrong in the table. Say which file a count is
about, every time.

### ~~LATENT, found while fixing this, deliberately not changed~~ — FIXED 2026-08-26

`169_build_identifier_graph.py` decided "ruled Native" as

```python
if classification_ruling not in ("", "UNRULED", "place_name_coincidence"):
    np_ruled_native.add(ein)
```

That is an **allow-list of negatives**, which is the wrong polarity: any new
negative-ruling token silently becomes *ruled Native*. Writing
`not_a_native_entity` — the obvious value — would have done exactly that, which
is why `code/251` reuses the existing `place_name_coincidence` token instead.

**FIXED.** 169 now calls `cedar_domain.np_ruling_is_native()`, an **allow-list
of POSITIVES** — `native_controlled`, `tribally_controlled`, `native_serving` —
declared once in `cedar_domain.py` beside `NP_CLASSIFICATION_NEGATIVE` and
`NP_CLASSIFICATION_UNDECIDED`. An unrecognised token is **UNKNOWN, never
Native**, and 169 now **counts and NAMES** every token in none of the three
declared sets, so a new vocabulary upstream is visible the day it lands instead
of being silently absorbed as a positive.

**Measured before changing it: 89 EINs read as ruled Native under BOTH tests.**
Zero behavioural difference today — which is the whole point. The defect was
never in what the line computed; it was in what the line would compute the day
somebody wrote the honest token. `code/251`'s reuse of
`place_name_coincidence` is still correct and should stay, but inventing a new
negative is no longer unsafe.

**A SECOND INSTANCE OF THE SAME SHAPE, IN THE SAME FILE, FIXED WITH IT.**
`169` also read `if tid and tier and tier not in ("C",):` and then handled `X`
in an inner branch — again an allow-list of negatives, so any tier token nobody
had enumerated propagated an attribution edge. It is now
`if tid and tier in (Tier.A.value, Tier.B.value):`. `norm_tier()` already
restricts the vocabulary to {A, B, C, X}, so this too is behaviour-identical
today.

**AND A THIRD, IN `70_key_unjoined_datasets.py`.** Found by grepping for the
shape rather than for the file:

```python
ruled = (funnel_stage == "ruled_native_verified"
         or ruling_authority not in ("", "agent_research"))   # NEGATIVES
```

`ruled` **suppresses** a tier-A demotion, so a new authority token —
`agent_research_two_leg`, `vendor`, `web_verified` — would silently have
counted as an owner ruling and kept a risky A. That is **regression rule 4
failing open** ("never treat agent research as Elijah's ruling"). Now an
explicit `OWNER_RULING_AUTHORITIES = {"elijah_ruling"}`. Measured in
`np_orgs.csv`: `''` 12,362 · `agent_research` 375 · `elijah_ruling` 27 —
behaviour-identical today, correct when the vocabulary grows.

**Three other candidates were checked and are NOT this defect**, recorded so
nobody re-opens them: `154_build_fr_ex_parte_notices.py:1439/1531`
(`why not in ("no_native_token_in_name", "empty")`),
`94_rescan_universes.py:818` and
`171_build_individual_native_verification.py:646`. All three fail **safe** — an
unrecognised token produces an EXTRA review row or an EXTRA warning, never an
attribution. The test to apply is not "is this a `not in` over a list of bad
values" but **"which way does it fail when the list is incomplete?"**

---

## A STALE TIER IS A WRONG TIER, EVEN WHEN NOBODY PROMOTED IT (2026-08-26)

`docs/ANCSA_OWNERSHIP_RULING.md` flagged **204 tier-A subaward rows** the ANCSA
pass repointed, and reasoned that a tier-A row pointing at the wrong entity has
an over-stated A, because the evidence that earned the A was evidence for the
wrong thing. **Sound as a general rule, and the measurement says it is not what
happened here.** `code/249_audit_ancsa_tierA_subaward_repoints.py`:

`sub_native_tier` / `prime_native_tier` are not minted in `subawards.csv`. `41`
and `45` write them as a literal copy of `confidence_tier` from the ledger row
for that UEI. So the question is answerable exactly — read the origin row.

**All 20 distinct UEIs behind the 204 already point at the CORPORATION in the
ledger, and have since 2026-08-06.** Their tier-A rationale says so verbatim:

> *"Corrected 2026-08-06: 'goldbelt' is the ANCSA corporation's brand. Moved
> from the village GOVERNMENT to the CORPORATION — separate legal persons.
> Verified against a retrieved source"*

**The tier-A evidence was never evidence for the village government.** What was
stale in `subawards.csv` was the ENTITY column. The ANCSA pass did not repoint a
correct-A-wrong-entity row; it caught a stale copy up to a correction the ledger
had already made twenty days earlier.

**But staleness cuts both ways, and that is the real defect in the 204.** Seven
of the twenty UEIs — all Olgoonik — are **tier B** in the ledger today via
`agent_research_one_leg`, from the pass this file records as *"49 single-leg
rows were correctly demoted A -> B"*. `subawards.csv` still carried the
**pre-demotion A** on 93 rows.

| n | disposition | why |
|--:|---|---|
| **111** | KEEP A | origin row is tier A today and names the same corporation |
| **93** | DEMOTE A -> B | origin row is tier B today; the A predates its demotion |
| **0** | could not be established | every UEI had the row needed to decide it |

Applied by `code/250_demote_stale_tierA_subaward_rows.py` — two existing
columns, no entity touched, nothing promoted, nothing re-tiered to X, backup
tagged `.bak_2026-08-26_pre_250_demote_stale_tierA_subaward_rows`, re-read from
disk after. **Independent cross-check: scanned across the whole file, rows where
the subaward tier is A, the ledger tier is B and both name the same entity
number exactly 93** — 91 `sub_native_tier` + 2 `prime_native_tier`. The demotion
set is closed.

**The rule: a consumer that COPIES a tier owes the source a re-read.** An
inherited tier is correct only as of the moment it was copied. `subawards.csv`
is broadly out of step with today's ledger — thousands of rows sit at B where
the ledger now says A — and **that direction is a promotion and must not be
done by hand**; re-running `41` then `45` is the way, and it would also have
written these 93 B's by itself.

---

## AN OWNER RULING MUST BE APPLIED, NOT ONLY REPORTED (2026-08-26)

`167_link_nonprofit_family_via_ein_hub.py` found **27 links `np_orgs.tribe_id`
carries that an owner ruling forbids** — COLVILLE ROTARY, KIOWA COUNTY FARM
BUREAU, COWLITZ COUNTY DRUG COURT, CHICKASAW COUNTY HISTORICAL SOCIETY, JEMEZ
MOUNTAINS ELECTRIC FOUNDATION and 22 more. It set its own `cedar_link_tier = X`
and filed a review row, and **did not overwrite `tribe_id`, because that is
script 70's column** and patching another script's output is how the `09`
regression happens.

**That caution was right and it is not a disposition.** A forbidden link left
live in a shipping column is a defect with a note attached.

Every one of the 27 arrived by `containment` **with a state conflict already
recorded on its own row** (`resolver_containment;state_conflict:KS!=OK`) and
every one carries a ledger row that is tier X via `elijah_ruling` reading,
identically on all 27: *"Ruled by Elijah 2026-08-12: not a Native entity."*

**Resolved both ways, because either alone leaves it live:**

1. **`70_key_unjoined_datasets.py` now defers to the ruling at source.** New
   `ledger_negative_ein_rulings()`; `do_np_orgs` blocks on it before any name
   resolution. 70 previously consulted `excluded_by_prior_ruling` and
   `funnel_stage` and **never the ledger, which is where the owner's nonprofit
   exclusions actually live**. This is what survives a rebuild: `17` rebuilds
   `np_orgs.csv` from the IRS BMF, so an in-place patch alone would be reverted.
2. **`code/251_apply_np_ein_exclusions_to_np_orgs.py` applied it to the live
   file now**, on those 27 rows only — a narrow write, because re-running 70 is
   a WHOLE-FILE re-key against a spine that has grown 1,310 -> 1,534 since it
   last ran, which is the "re-running 57 loses work" trap.

**Only the blanket-negative grammar blocks.** *"not a Native entity"* is a
ruling about the ORGANISATION. Where a ruling names a different owner the answer
is a REDIRECT and never a block — corrections are made, never erased. And the
evidence of the refused match is kept: `tribe_id_token_match` and
`canonical_name_token_match` are untouched, and `entity_match_basis` now carries
the ruling verbatim with its provenance.

**Why this does not violate "repoint, don't blacklist".** That rule protects a
*correct* attribution from being suppressed by a node-level tier-X block in
`169`. Here the owner ruled the organisation is not Native, so there is no
correct attribution to suppress — and `169` was **already** blocking these 27
EINs on `np_orgs.cedar_link_tier = X`, which `167` set. This makes `tribe_id`
agree with a block the graph already honours.

**`entity_id` — the publishable key — was blank on all 27**, because 70 writes
it only at tier A. `251` asserts that rather than assuming it, and refuses
outright if a forbidden link is ever found in `entity_id`.

---

## 169 WAS NOT RE-RUN, AND WHY (2026-08-26 19:15)

`169_build_identifier_graph.py` is **stale**: it last ran at 17:57, before the
ANCSA writes (18:34), before `241` rewrote the ledger and the spine (18:59), and
before the 93 subaward demotions and 27 nonprofit exclusions above. It should be
re-run.

**It was not, because two writers are live on its inputs**, and the ordering
rule in this file says the full rebuild goes last:

| input | live writer |
|---|---|
| `data/clean/subawards.csv` | **`121_pull_subawards_api.py pull --sequential`, PID 13736, running since 17:19** — appends on completion; 105 minutes at `rows_so_far=0` against a host returning `TRANSPORT_FAILURE`, but it is an armed writer |
| `data/clean/cedar_identifier_ledger_final.csv` | the individual-Native-firm agent — `241` wrote the ledger **and the spine** at 18:59, `244` landed at 19:04 |

A graph built from a ledger another agent is still appending is a snapshot of an
inconsistent moment, and 115,471 graph nodes is exactly the artefact a later
reader quotes as settled.

**To run it, once 121 has exited and the 24x agent is done — no arguments, no
network:**

    py -3 code/169_build_identifier_graph.py

Nothing else is blocked on it. Its inputs already carry every write from today,
so the re-run is a single command whenever the window opens.

---

## GATE FAIL 2026-08-26 19:10 — NOT the labor-employment build. Owner named.

Recorded under standing rule 15, which forbids writing "pre-existing, not mine"
and continuing. This names it and its owner instead.

**The failing metrics:** `tables_missing_from_25_TABLES` 234 → 238 and
`tables_missing_from_27_SPEC` 249 → 253. Both are "only goes down" metrics.

**The four tables that landed, with creation times:**

```
19:59:02  individual_native_firm_register.csv
19:01:02  individual_native_firm_contracts.csv
19:01:02  individual_native_firm_contracts_published.csv
19:10:09  contractor_ranking.csv
```

**Owner: the individually-Native-owned-firm build (`code/170_build_individual_
native_candidates.py` → `171` → `172_write_individual_native_codebook_
fragment.py` → `173_refresh_individual_native_results_section.py`), plus
`code/25_build_publication_layer.py`, WHICH WAS STILL RUNNING WHEN THE GATE
FAILED** — `contractor_ranking.csv` was created at 19:10:09, i.e. by that live
process, seconds before the measurement. `276_measure_discovery_gap.py` and
`284_audit_nondeterministic_keys.py` were live in the same window.

**So the gate is measuring a half-finished registration chain, and the remedy
it prescribes — "re-run the full 7-step ship chain (`py -3 code/build.py ship`; “87 → 25 → 27” is a 3-step shorthand that omits the codebook build, the gate, the coverage profile and the harmonised views)" — is the thing its owner is executing.**
That is a real finding about the metric, not only about this session: *a gate
that reads a shared directory mid-write reports another agent's incomplete step
as a regression*, and the next agent will spend an hour on it unless it is
written down. Compare creation times against the live process list before
believing it.

**Proven not to be the 158/262/264/265/266 work:** every table this session
wrote already existed and was already inside the 234 —
`gaming_employment_observations.csv`, `gaming_facilities.csv`,
`gaming_ordinances.csv`, `ca_gaming_facilities_official.csv` and the ten hub
tables 164 re-links. **This session created ZERO new files in `data/clean/`.**
Measured before and after: the same gate run at 18:49 and again at 18:56, with
the merge and the attribution repair landed between them, reported
`tables_missing_from_25_TABLES = 234` **both times**. The metric moved only
after 18:59, when the four files above appeared.

The one gate metric this session did move, it moved and then fixed: appending
36 columns to `gaming_employment_observations.csv` (32 from the 158 merge, 4
from the 262 repair) dropped `07n_gaming_employment` under the 0.60 match gate
and pushed `tables_missing_codebook_block` 140 → 141. `code/263` registered all
36 in the fragment; the metric is now **139**, better than the 140 it started
at, and `codebook_undocumented_public` stayed **0**.

### 19:14, same gate run — a SECOND, DIFFERENT owner's failure appeared

```
!! files_with_columns_lost_vs_backup = 1, must be 0
!! contractor_ranking.csv  44 -> 43 columns vs contractor_ranking.csv.bak_2026-08-26_pre269
```

**Owner: `code/269_*`** — the backup tag names it. That script dropped a column
from `contractor_ranking.csv`, a file created twelve minutes earlier by
`25_build_publication_layer.py`. Script numbers **269, 276 and 284** were all
claimed by other agents during this session; this one is not in the 262–268
block this session used.

Meanwhile `tables_missing_from_25_TABLES` moved **238 → 237** between two gate
runs four minutes apart with no intervening action from this session — the
registration chain is still catching up on its own.

**The rule this earns: on a machine running many agents, a single gate reading
is a SNAPSHOT OF A MOVING FILESYSTEM, not a verdict on the caller's work.**
Standing rule 15 is still right that a FAIL is stop-work and must never be
waved away — but the discharge of it is to identify the owner by evidence
(creation time, backup tag, live command line), which is what the two entries
above do. Verify your own files directly instead: every file this session wrote
was re-read after writing and checked against its own pre-backup —

```
gaming_employment_observations.csv     769 -> 3,246 rows   25 -> 62 cols   0 lost
gaming_facilities.csv                  784 ->   787 rows  104 -> 104 cols   0 lost
gaming_ordinances.csv                1,155 -> 1,155 rows   70 ->  73 cols   0 lost
ca_gaming_facilities_official.csv      245 ->   245 rows   27 ->  29 cols   0 lost
```

**`files_with_columns_lost_vs_backup` names the offending file AND its backup
tag on the failure line.** That is the metric doing its job perfectly: it points
at `pre269`, not at `pre158`/`pre262`/`pre264`/`pre265`/`pre266`. Read the tag
before assuming the failure is yours.

---

## 2026-08-26 ~19:15 — `contractor_ranking.csv` IS SCRIPT 269's, NOT SCRIPT 25's, AND IT IS NOW REGISTERED

**Correction to the section immediately above.** It reads
`contractor_ranking.csv` "was created at 19:10:09, i.e. by that live process
[`25_build_publication_layer.py`]". It was not. `data/clean/contractor_ranking.csv`
is written by **`code/269_build_contractor_ranking.py`**, which is mine, and the
19:10 stamp is that script's *second* run — the first landed at ~19:03 and the
second dropped one column. Script 25 does not create tables in `data/clean/`; it
reads them into `dist/`. The inference "a live process wrote it because it is new"
is the right instinct applied to the wrong process list, and it is worth keeping
as the shape of the error: **a file's mtime tells you WHEN, never WHO. Grep
`code/` for the filename before assigning an owner.**

The broader point that section makes — that a gate reading a shared directory
mid-write reports another agent's incomplete step as a regression — still stands
and is correct.

### Disposition of the +4 on `tables_missing_from_25_TABLES` / `_27_SPEC`

The four files that moved the metric after 18:59, and who owns each:

| file | owner | status |
|---|---|---|
| `contractor_ranking.csv` | `code/269_build_contractor_ranking.py` (this session) | **REGISTERED** |
| `individual_native_firm_register.csv` | `code/241_promote_individual_native_firms_in_place.py` | **open — not mine to describe** |
| `individual_native_firm_contracts.csv` | `code/242_build_individual_native_firm_contracts.py` | **open — not mine to describe** |
| `individual_native_firm_contracts_published.csv` | `code/242_build_individual_native_firm_contracts.py` | **open — not mine to describe** |

**Mine is done.** `contractor_ranking.csv` now has:

- a codebook FRAGMENT — `data/clean/codebook/02h_contractor_ranking.csv` and
  `docs/codebooks/02h_contractor_ranking.md`, 43 variables, one marked internal.
  `codebook_master.csv` deliberately untouched; reconciling master from fragments
  is `cedar_register_codebook.py`'s job and its owner's timing.
- an entry in `25_build_publication_layer.py::TABLES` (an override, because the
  index columns are a compound of an owner key and a firm key that the codebook
  registry cannot guess).
- an entry in `27_build_dataset_manifests.py::SPEC` under the key
  `contractor_ranking` — **separate from the existing `contractors` descriptor
  on purpose.** That one describes the identifier ledger, a link table. This one
  describes a ranking of owners by dollars. `measure` is the field a subscriber
  cites, and one manifest cannot honestly claim two measures.

Metric moved **238 → 237** and **253 → 252**. The residual **+3 on each is the
241/242 register**, and the reason I have not closed it is not convenience:
**a manifest is an AUTHORED claim about what a dataset measures, and I did not
build those tables.** Writing a `measure` and a `universe` for someone else's
individually-Native-owned-firm register would be the consumer assigning a
description by another name — the same shape as the consumer assigning a tier.
The owner of 241/242 should add two `SPEC` entries and two `TABLES` rows and the
gate goes green.

### One column was deliberately removed, and it tripped rule 12

The 19:10 run dropped `firm_top_funding_agency` from `contractor_ranking.csv`,
43 columns against the 19:03 file's 44, and the gate correctly raised
`files_with_columns_lost_vs_backup = 1`. **The removal was deliberate and the
detector was right to ask.** `prime_contracts.funding_agency` holds two
vocabularies split at the FY2016/FY2017 archive boundary — the same seam as
`extent_competed` — with **no authoritative code column on our side**, so a
per-firm modal agency computed across a firm's whole FY span picks whichever
vocabulary happened to carry more dollars. It is an era label wearing an
agency's name. Dropped rather than caveated, because nothing in the ranking
needs it.

Both 19:03 backups were superseded drafts of a table twenty minutes old with no
consumers, and are in `graveyard/2026-08-26_269_superseded_drafts/` rather than
deleted. `files_with_columns_lost_vs_backup` is back to **0**.

**The rule this earns, for anyone adding a column to a NEW table:** a
`.bak_*` written by the *same script's previous run in the same session* is a
draft, not a prior release, and rule 12 cannot tell the difference. Move it to
`graveyard/` with a note, never delete it, and say in writing which column went
and why — the detector's whole value is that it makes you write that sentence.

### Standing note for any competition or agency cut in the `contractors` shelf

`extent_competed_normalized` (DAIMS-DEC v2.2, written by `code/207`) is the only
column a competition claim may use; the raw `extent_competed` selects an ERA.
Neither `prime_contracts_awards.csv` nor `prime_contracts_published.csv` is safe
for this — `79_build_award_level_contracts.py` copies the raw value, so an award
straddling FY2016/17 inherits whichever vocabulary its first row used.
**`funding_agency` has the same two-vocabulary problem across 176,973 rows and
no normalised counterpart exists.** Restrict to one era and say so, or drop it.
`docs/DRAFT_top_native_federal_contractors.md` makes no competition claim and no
agency cut, for this reason.

### TWO DETECTORS FOR ONE CLASS — merge them (2026-08-26 19:15)

While `code/248_audit_tier_inheritance_patterns.py` was being written, another
agent independently landed **`code/293_lint_bug_classes.py`**, an `ast`-based
linter for six named defect classes — and one of its classes is this one
(`tier = "A" if meth in RULED else ...`, its line ~528). Two agents reached for
the same countermeasure within an hour of each other, which is decent evidence
the class is real and the reflex is right.

**It is still one detector too many to maintain.** `293` is the more general
tool. What `248` holds that `293` does not:

* a **per-site recorded disposition table** — every place in `code/` where a
  tier assignment sits beside a ruling-method test, with a verdict made by
  reading the code and the reason written out, so a regex hit that is fine
  stays fine and only NOVELTY raises;
* a **re-derived ledger exposure measurement** — how many rows a consumer would
  promote away from their true tier today (380, of which 344 are tier X), so
  the number in any report is measured rather than quoted.

**Fold those two into `293` and retire `248`.** Until that happens, `248`
carries `293` in its own disposition table as CLEAN with this note, so neither
flags the other as a defect.

---

## NAMED GATE FAILURE — registry lag, owner is the live publication-layer build (2026-08-26 ~19:20)

Named here by `code/276_measure_discovery_gap.py` (the discovery-gap measurement)
under CONCURRENCY RULE 3 / standing rule 15, which require a gate failure that
belongs to another agent to be named with its owner **before** anyone continues.

**Failing metrics, measured after my work:**

    tables_missing_from_25_TABLES   ROSE 234 -> 237
    tables_missing_from_27_SPEC     ROSE 249 -> 252

**It is not mine, and that is checkable rather than asserted.** This session
wrote exactly four things and **none of them is a table in `data/clean`**:

| written | where |
|---|---|
| `code/276_measure_discovery_gap.py` | `code/` |
| `docs/DISCOVERY_GAP.json` | `docs/` |
| `_pull_universe.csv` | `data/raw/contracts/usaspending_transactions_2026-08-06/` |
| doc edits to `PULL_DISCIPLINE.md`, `ASSUMPTIONS_AND_LIMITATIONS.md`, this file | `docs/`, root |

`62` counts only `data/clean/*.csv`, so a session that adds none cannot move
either metric.

**The owner: the publication-layer / gaming builds that are LIVE right now.**
Between 18:52 and 19:20 the following landed or were rewritten by concurrent
agents — the whole gaming family at 19:09, `contractor_ranking.csv` at 19:13 —
and the two registry builders themselves were edited mid-session:

    code/25_build_publication_layer.py   modified 19:13   <- builds registry 25
    code/27_build_dataset_manifests.py   modified 19:17   <- builds registry 27
    code/269_build_contractor_ranking.py                  <- new table
    code/264_add_missing_osha_tribal_facilities.py
    code/265_merge_osha_relift_rows.py
    code/266_apply_gaming_hub_spillover_rulings.py

**The registries the gate checks against are being rebuilt by a live process
while the gate reads them.** That is the whole failure: tables are landing
faster than the full 7-step ship chain (`py -3 code/build.py ship`; “87 → 25 → 27” is a 3-step shorthand that omits the codebook build, the gate, the coverage profile and the harmonised views) is being re-run, so the count of unregistered tables
rises for as long as the builds outpace the registration step. It is a LAG, not
a defect in any one table.

**What has to happen** (`docs/SHIPPING_RUNBOOK.md`): whichever agent owns the
gaming / publication-layer build registers a codebook block for each new table
and re-runs **the full 7-step ship chain (`py -3 code/build.py ship`; “87 → 25 → 27” is a 3-step shorthand that omits the codebook build, the gate, the coverage profile and the harmonised views)**. Both metrics fall on their own once it does —
the same run that fixed `individual_native_firm_register.csv` earlier this
evening took `ship_tables_at_zero` 206 -> 138 and
`tables_missing_notes_contract` 206 -> 139 without anyone touching a table.

**Do NOT re-baseline either metric to clear this.** `--baseline` records a
floor; it is not an acknowledgement button, and baking a rising count into the
floor is exactly how the `codebook_undocumented_public = 45` line survived six
sessions.

**The rest of the gate is green and moved the right way in this window:**
`ship_dist_rows` 5,227,896 -> 7,444,208, `ship_tables_shipping` 49 -> 125,
`ship_tables_at_zero` 205 -> 138, `codebook_variables` 2,188 -> 2,779,
`spine_entities` 1,489 -> 1,534, `tier_A_ruled` 1,634 -> 1,676. The two rising
metrics are the trailing edge of that same work, not a contradiction of it.

### The rule this earns

**A gate metric that counts REGISTRATION can be pushed red by a build that is
still running, and a red-because-still-running is not the same as a
red-because-broken.** The two look identical in the output. The discriminator
is cheap and must be recorded whenever this metric fails: check whether the
registry BUILDERS (`25_`, `27_`, `87_`) have an mtime inside the current
session, and whether `Win32_Process` shows a live build. If both are true, name
it and hand it back; if neither is, it is a real omission and belongs to
whoever landed the table.

**CONFIRMED WHILE THIS NOTE WAS BEING WRITTEN.** Three consecutive `62` runs over
about ten minutes: `tables_missing_from_27_SPEC` went 249 -> 252 -> **cleared**,
with no action from this session, because the owning agent re-ran its registry
build in between. `tables_missing_from_25_TABLES` is still at 237 and is
expected to clear the same way. That is the lag hypothesis above confirming
itself in the output, and it is the reason the discriminator is worth running
before anyone "fixes" this metric.


---

## THE SIX NAMED DEFECT CLASSES — recognise the SHAPE (2026-08-26)

**Every one of these was found MORE THAN ONCE on a single day, in unrelated
scripts, by different agents. Not one was found by looking for it. Each was
fixed only where somebody tripped over it, so the same defect stayed live in
five, nine, thirty other places while its write-up sat in a document.**

Script 88's additions glob was named in `docs/FACT_CHECK_2026-08-06.md` finding
B-1. It was fixed three weeks later, and on the day it finally got swept it was
still live in nine other scripts. **The diagnosis was never the hard part. The
hard part is that a defect fixed in one place leaves no trace in the other
nine.**

So they are numbered here, with the real example each is named after, and
`code/293_lint_bug_classes.py` detects all six by AST. **`62_no_regression_check.py`
carries `lint_new_defect_instances`, which MUST BE 0, and every per-class
counter as MUST_NOT_RISE.** Full audit, with every instance by file and line and
the 285 scripts checked and found clean: **`docs/CODE_HEALTH_AUDIT.md`**.

    py -3 code/293_lint_bug_classes.py            # check against the floor
    py -3 code/293_lint_bug_classes.py --class 6  # one class, with the reason
    py -3 code/293_lint_bug_classes.py --selftest # prove the detectors still work

---

### DEFECT 1 — reading the ADDITIONS and never the LEDGER

`glob("deals_*_additions.csv")` reads the ADDITIONS to the deals table and never
the table. **A 790-row deals master held exactly ONE row dated 2026 while 131
verified rows sat in two root CSVs.** Found in `88`, `57`, `41`, `82`, `35`,
`33`, `59`, `73`, `31`, `175` across three sessions.

**The rule.** A CONSUMER — counting, joining, auditing, profiling — reads the
PROMOTED table and nothing else. Only a PRODUCER reads the parts, and it must
read EVERY part. `160_ship_gap_report.py` reporting *"7,009 rows in 8 root CSVs
no registry enumerates"* is the same defect wearing a different label.

**Declared once, in `cedar_domain.PROMOTED_TABLES` /
`PROMOTED_TABLE_PRODUCERS` / `DEALS_TRUTH`. Import it; never glob.** Add a
family the day it is created, not the day it is miscounted — the detector is
only as wide as that dict, and today it holds exactly one family.

### DEFECT 2 — our own defect published as a FACT ABOUT THE SOURCE

The most expensive class, because the output looks like a finding.

**2a. `setdefault` on a key that already exists is a NO-OP.**
`row = {k: "" for k in FIELDS}` creates every key holding `""`, and `setdefault`
only writes when a key is ABSENT. `119_build_digital_and_loyalty.py` shipped
`tier` blank **154/154**, `confidence_tier` blank **10,661/10,661**,
`period_type` **10,660/10,661** — and a downstream agent reported it as *"the
source records no tier"*. Two more found and fixed 2026-08-26:
`107_pull_remaining_states.py` (`fetched_date` blank on **494 of 494** rows of
`state_gaming_observations.csv`) and `94_rescan_universes.py`.
**Write `x[k] = x.get(k) or DEFAULT`.**

**2b. An absent column name reads as an empty source.** `102` counted two
datasets on a `tribe_id` column NEITHER FILE HAS — both key `tribe_entity_id` —
and printed **0.0% coverage for 19 days** while they held 307 and 274 keyed
rows. **A coverage computation must RAISE on a missing column, never print a
zero.**

**2c. A drop counter that does not NAME what it dropped.** `87` counted
`"skipped: not a documented dataset"` and never printed the filename — **33,817
rows invisible for twenty days.** A count is not actionable and does not accuse
anyone of anything, so it scrolls past. **A filename is a task.** 60 more
counters carry this shape today; they are listed by file and line in the audit.

### DEFECT 3 — a RULED method treated as a POSITIVE ruling

`148_resolve_schedule_i_recipients.py` did `tier = "A" if meth in RULED`. **All
317 `elijah_ruling` EIN rows in the ledger are tier X — NEGATIVE rulings.** It
promoted exclusions into confident attributions: `COLVILLE ROTARY -->
Confederated Colville`, tier A.

> **A RULED method says a HUMAN DECIDED. It never says the answer was YES.**

Same class: an agent read `status = SETTLED` as confirmation when the `outcome`
was `HOLD_OVER_OWNER` / *"HOLD — RETRACTION REQUIRED"*.

> **`status` says the ruling was PROCESSED. `outcome` says what it DECIDED.**

This is the tier-inheritance rule from the top of this file, arriving by a
different road: **a tier is INHERITED from the source row, never assigned by the
consumer**, and the exactness of the KEY says nothing about the correctness of
the LINK.

### DEFECT 4 — a per-unit budget that TRUNCATES and then marks COMPLETE

`PER_DOCKET_BUDGET_S = 240` wrote four FERC dockets at **2,300–3,200 of
3,555–4,847** documents, then marked them `done`, so **no resume would ever
revisit them**. Nothing looked wrong: each sheet was well-formed and the run
reported success.

**The only thing that exposed it was comparing `documents_retrieved` against
`total_hits_reported_by_source`.** Do that wherever a source states a total, and
**refuse to write `done` when they differ.** Eight scripts still carry a budget
that can truncate with no such comparison — mostly CDX and probe runs where
stopping early IS the design, and where the defect is therefore not the stop but
the artefact failing to say *"stopped on the clock, at N of M"*.
`62`'s `units_short_of_source_reported_total` is the runtime backstop.

### DEFECT 5 — a NON-IDEMPOTENT build

`164` short-circuited on a column test and silently **rewrote its own log with
187 facilities reading "0 sources"** — facilities holding thousands of metric
rows each. **Re-running a build must not change its output.** The shape: an
"already done" guard skips the work, the run still rewrites its log wholesale,
and on the second run every counter is zero and the log says so — truthfully
about that run, and misleadingly about the world. Six scripts still carry it.

Decide which your log means: *what this run did* (then say "incremental run, N
already present") or *what the table now holds* (then recompute from the table,
never from the run's counters). `164` chose the second and says so.

### DEFECT 6 — a FULL REBUILD silently reverting an IN-PLACE ENRICHER

`133 build` discarded **931 entity links and nine columns** that `168` had
written four minutes earlier — and **printed a LARGER row count, which read as
pure progress.** `09` has done the same to `50`. `41_build_codebooks.py` writes
the master in `"w"` mode and would now delete **21 of 43 blocks**. `119` would
revert `164`'s column block. Re-running `57` rebuilds from the CURRENT spine and
repointed Confederated Salish and Kootenai onto that tribe's college.

> **A full-rebuild stage and an in-place enricher on one file need an ordering,
> and THE ENRICHER RUNS LAST.** A `.bak_<date>_pre_<script>` file beside an
> output is the signal that an enricher has touched it.
>
> **A partial restore is a rebuild revert wearing a different hat.** Restore the
> whole set or none of it.

**`docs/CODE_HEALTH_AUDIT.md` now carries the full map: 32 tables with a
conflicting pair, and 45 tables with more than one writing script, with the
scripts named per table.** Seventeen of those pairs had never been written down
anywhere. `docs/lint_bug_classes.json` holds the machine-readable version under
`class6_io_map`.

**Known limit, stated rather than papered over:** a read-then-rebuild-from-
elsewhere is indistinguishable from a read-then-enrich by static analysis, so
`prime_contracts.csv` — whose five writers all read it first — does NOT trip
class 6, even though `START_HERE.md` records that a rebuild reverts
`207_normalize_extent_competed.py`. For a table with many writers, the ordering
has to be written down by a person.

---

### HOW TO SILENCE A FINDING, AND HOW NOT TO

    # lint-ok: class1 - 153 is the promoter; reading the parts IS the job

On the flagged line or anywhere in the comment block above it. **A reason is
required.** Waived findings are counted and listed in every run, never hidden —
this project counts what it drops, by name, and the linter obeys its own rule.

**`--baseline` records a floor. It is not an acknowledgement button.** And
`--selftest` exists because a detector narrowed until it stops seeing the defect
it was built for is worse than no detector: it reports clean.

---

## NAMED FAILURE — a new class-4 instance, owner identified (2026-08-26 19:16)

Per standing rule 15 option 3, and the first thing the new check caught — four
minutes after it was wired into the gate.

`code/215_pull_nm_revenue_sharing_quarters.py:67` and
`code/217_pull_az_adg_report_archive.py` are **new class-4 instances**: a
`RUN_DEADLINE` exits the fetch loop, the file writes `finished`, and neither
compares what it retrieved against a total the source reported. 215 was written
**19:14:54**, ninety-six seconds before the gate first ran; 217 appeared at
**19:25:05**, while this section was being written. Both are the same shape as
`213` and `214`, which are inside the floor.

**OWNER: the agent working New Mexico / Arizona gaming regulators** (work-queue
item 9 — `gaming.az.gov` and `www.nmgcb.org`; the same author holds `211`–`217`).
**This is live work, not abandoned work; editing it would race its author.**

**WHAT HAS TO HAPPEN:** record NM's own reported document/quarter count beside
what was retrieved, and refuse to write `finished` when they differ — one field
and one comparison. Then `py -3 code/293_lint_bug_classes.py --baseline`.

Also observed and self-resolving: `code/227_anomaly_sweep.py` did not parse for
about four minutes while it was being written, and the linter printed it under
**NOT PARSED — these were NOT checked, and that is not the same as clean.** It
parses now. A file the linter could not read has been checked for nothing, which
is why that line is loud rather than a silent skip.

---

## THE INDIVIDUALLY NATIVE-OWNED FIRM CLASS REACHED THE SPINE (2026-08-26)

The class was ruled into existence in this file on **2026-08-07** and for
nineteen days it lived in three documents and **zero spine rows**. Measured
before `code/241_promote_individual_native_firms_in_place.py` ran:

    owner's individual-Native rulings                          45
      ...matching a ledger row                                 42   (X 33, C 9)
      ...with a BLANK tribe_id                                 40
    prime_contracts rows reached by them                   16,910
      ...all attributed_flag = 0, tier C, tribe_id blank
      ...obligations                              $2,340,066,582.34

**Same failure as the NHOs — 218 registered, 31 in the spine.** A discard pile
is what a ruled category looks like when nobody built it a home. Now: **45
spine rows** in `entity_class = "Individually Native-owned business"`, 42 ledger
identifiers bound at tier A `elijah_ruling`, `tier_A_ruled` 1,634 → 1,676.

### Four things the next agent must not undo

1. **The class is the FIRM, never the person.** The key is a Cedar surrogate
   (`CEDAR-ENT-nnnnnn`), deliberately not a mnemonic slug — a slug built from a
   sole proprietor's name mints the disclosure into the primary key of every
   downstream join. RULE NEEDED #1 in the class proposal stays open; the
   surrogate satisfies it either way it is answered.
2. **`parent_native_entity` is permanently NULL, every row is self-parented,
   and `bears_ownership()` refuses every edge on the class in both
   directions.** No tribal, ANC or NHO total changes — these firms were never
   in one. `owner_self_identifies_with` is in `NEVER_OWNERSHIP`: *"owned by
   individual Cherokees"* (38 of 45 rulings) is a fact about a PERSON and never
   keys a `tribe_id`.
3. **`prime_contracts.csv` was NOT written.** The class's $2.34B is rolled up
   in its own tables by `code/242`. Writing it into `attributed_flag` would
   inflate the $244.77B flagship figure by summing two classes that move in
   opposite directions (the individual class is larger by rows, smaller by
   dollars).
4. **A RULING IS NOT TIER A BECAUSE ITS METHOD IS "RULED".** `elijah_ruling` is
   in `RULED_METHODS` whether the owner said YES or NO. `241` branches on the
   ruling's **OUTCOME** through an exhaustive map, aborts on an unrecognised
   one, and records `tier_source` on every row. This is the defect that made
   `148_resolve_schedule_i_recipients.py` publish 317 tier-X exclusions as
   tier-A attributions.

### THE INVERTED RULING, and the two rows it had already corrupted

**Five rulings read "Not a Native entity – individually Native-owned firm."**
That refuses the TRIBAL LINK, not Native ownership. Read literally it inverts
the owner's meaning — and it already had:

    CAGE 9DVK5  SAN JUAN SERVICES LLC   tier X, tribe_id TRBF-SNJUAN-00,
                entity_class FEDERAL_TRIBE_LOWER48,
                "Ruled by Elijah 2026-08-12: not a Native entity"
    CAGE 9H8M8  FOUR CORNER PEST CONTROL LLC -> TRBF-TEMOAK-00, same shape

`09`'s `NOT_NATIVE_RE` matched the leading clause and left the tribal binding
the ruling was *refusing* in place. Both repointed, declared up front so a
correction that fails to fire aborts the run. Ask
`cedar_domain.is_tribal_link_refusal_not_native_refusal()`; never match the
words "not a Native entity".

**Exclusions are scoped to an (identifier, entity) PAIR and block the NAME path
too** — `data/clean/individual_native_exclusion_pairs.csv`. A blanket block on
the identifier suppresses a correct attribution elsewhere; blocking only the
identifier hands the same match back through the name-based resolver.

### Privacy: a SECOND restriction, independent of D&B, that survives any answer

May publish: contract facts, class totals, distributions. **May not publish, in
bulk or singly: legal/DBA/owner name, address, any person↔ancestry pairing, and
the UEI where the legal name is a person's** — SAM's public search resolves a
UEI to that name, so publishing the UEI publishes the name by one hop. Cells
under 3 firms are suppressed and the suppression is reported (375 of 613).
Cedar Press's own policy is inherited, not restated (`nrc_meeting_participants`,
`ferc_ex_parte_parties`). **A firm's website statement is our EVIDENCE, never
its PERMISSION**: `consent_status` is `NOT_ASKED` on all 45.

Absence is `NO_CLAIM_FOUND`. **There is no `NOT_NATIVE` in this schema** and
`cedar_domain.absence_value_ok()` refuses to write one. Measured here: **76.7%
of this class's dollars carry no Native set-aside of any kind**, against 57.2%
project-wide — absence of a flag is not evidence against.

### Two latent defects this work exposed in shared scripts, both fixed

- **`25_build_publication_layer.py` never made the TABLE name SQL-safe**, only
  the columns. `advocacy_passthrough_2026-08-07.csv` (dated 2026-08-07) yields
  three bare hyphens in a `CREATE TABLE`, which sqlite reads as subtraction —
  and the abort lands *after* `dbpath.unlink()`, leaving a partial database
  where a complete one was. Fires for any registered table whose filename
  carries a date.
- **Excel truncates a sheet name to 31 characters** and `25` did not
  de-duplicate the truncation, so two long table names abort the workbook after
  the DB is written. It caught a second, unrelated pair immediately:
  `sam_prime_contracts_fy2000_2007` vs `..._publishable`.

---

## NAMED GATE FAILURE — `lint_new_defect_instances`, owner identified (2026-08-26 ~19:45)

Per standing rule 3. `62_no_regression_check.py` FAILS on **one** metric:

    lint_new_defect_instances = 3, must be 0

All three are named by `293_lint_bug_classes.py` and **none is in
`code/241`–`code/244`** (verified by grepping 293's own output for those
scripts — no hits):

| class | script | mtime |
|---|---|---|
| class4 | `215_pull_nm_revenue_sharing_quarters.py` — `if time.time() > RUN_DEADLINE:` | 19:18 |
| class4 | `217_pull_az_adg_report_archive.py` — same line | 19:29 |
| class6 | `97_build_aliases_and_relationships.py` — `entity_relationships.csv` | 19:29 |

**OWNER: the agent(s) writing `code/215_*`, `code/217_*` and editing
`code/97_build_aliases_and_relationships.py`.** All three files were written or
modified at 19:18–19:29 today, i.e. *after* `293` recorded its baseline at
19:18 and while those agents were live. This is in-flight work, not abandoned
work.

**WHAT HAS TO HAPPEN:** fix the two class4 deadline checks, or waive each line
with a reason (`# lint-ok: class4 - why`) — a waiver is counted and named by
293, never hidden. For the class6 instance, establish the ordering between the
full-rebuild writer and the in-place enricher on `entity_relationships.csv` and
make the **enricher run last**.

Everything else in the gate is green and nothing was lost: the three trap
metrics (`files_with_columns_lost_vs_backup`,
`units_short_of_source_reported_total`,
`coverage_columns_that_do_not_exist`) are all **0**, `ship_dist_rows` rose
5,227,896 → 7,444,230, `ship_tables_shipping` 49 → 126, and every registration
metric this session's tables touched went DOWN, not up:
`ship_tables_at_zero` 205 → 138, `tables_missing_codebook_block` 144 → 139,
`tables_missing_notes_contract` 206 → 139. `tables_missing_from_25_TABLES` and
`tables_missing_from_27_SPEC` both rose by 3 when the four new tables landed and
were **closed the same session** by registering them, not by re-baselining.

---

## TWO DETECTORS FOR ONE CLASS: 248 IS RETIRED, 293 IS THE ONE (2026-08-26, ~20:00)

`code/248_audit_tier_inheritance_patterns.py` and `code/293_lint_bug_classes.py`
were built the same evening, by different agents, for overlapping classes. 248's
own author reached the conclusion and wrote it into 248's disposition table:

> "Two detectors for one class is one too many to maintain. 293 is the more
> general tool and should absorb this file's value; what 248 has that 293 does
> not is the per-site RECORDED DISPOSITION table and the re-derived LEDGER
> EXPOSURE measurement. **Fold those into 293 and retire 248.**"

Done. **Two detectors drift, and a drifted detector is worse than none, because
it is trusted.**

### Where each piece went

| 248 had | it is now |
|---|---|
| `DISPOSITIONS`, one verdict + written reason per site | `293.DISPOSITIONS`, carried over verbatim, plus new entries for `97` (now FIXED) and `310` |
| exit non-zero on a site with no recorded disposition | `293.disposition_findings()` raises it as a **class-3 finding** - which is STRICTER, because `62_no_regression_check.py` tracks `lint_class3` as MUST_NOT_RISE, so an unreviewed site now fails the GATE and not just one script |
| `measure_ledger()` | `293.measure_ledger_exposure()`, still re-derived from the file, and now importing `cedar_domain.RULED_METHODS` instead of keeping a fourth copy of it |
| the syntactic scan | `293.scan_tier_sites()` |

**248 is a stub, not a deletion.** Its number is referenced by `AGENTS.md`,
`START_HERE.md` and `docs/NONPROFIT_ENTITY_LINKAGE_BUILD_LOG.md`; deleting it
would turn those into dead pointers, which read like a missing tool rather than
a moved one. The stub prints where the work went and **exits 2** - because a
retired detector that exits 0 reports CLEAN, and a check that reports clean
without looking is the worst object in this repository.

### A new capability the fold-in adds: 293 prunes its own table

293 now also prints **the dispositions whose site no longer matches the scan**
(9 of them today: `34`, `70`, `91`, `147`, `167`, `169`, `172`, `173`, `174`).
That is not a failure - the file was fixed, or the pattern moved - but a
disposition table nobody prunes stops describing the code. They are kept,
because deleting the record deletes the reasoning; they are now *visible*.

---

## CLASS 7 - A POSITIONAL OR NON-DETERMINISTIC PRIMARY KEY (2026-08-26)

Added to `293_lint_bug_classes.py` as the seventh named class, and to
`62_no_regression_check.py` as `lint_class7`, MUST_NOT_RISE.

> **A column can be unique in EVERY build and still be a corrupt key.**

Three measured instances, which are the fixtures the check must never stop
finding:

| id | shape | what was measured |
|---|---|---|
| `ferc_filing_id` | `abs(hash(filer_organization)) % 10000` | Python randomises string hashing per process: **4 of 2,534** documents shared between the 08-12 and 08-26 builds kept their id |
| `INV-nnnn` / `verification_id` | RANK-derived | a concurrent rewrite of `prime_contracts.csv` shifted every rank below the insertion point, and **Cherokee Construction briefly carried Frontier Electronic Systems' ownership sentence and URL**. Nothing errored |
| `EMP-OSHATRIBE-*` / `observation_id` | POSITIONAL | on a re-run **482 of 492 rows changed id**; re-running the merge would have appended **492 silent duplicates** |

**293 CONSUMES `code/284_audit_nondeterministic_keys.py` rather than
re-deriving it.** 284 landed first and published `lint_key_stability()` and
`lint_self_test()` specifically for 293 to adopt, saying in its own source: *"A
second lint would be a second thing to run and a second thing to forget, so this
is deliberately NOT a runner."* Duplicating its patterns here would have
rebuilt, on the same day, the exact mistake that retired 248.
`293 --selftest` now runs **284's three fixtures too**, so the single entry
point proves every class it reports on.

**Count today: 74 unwaived** (51 POSITIONAL, 15 OBJECT_ADDRESS, 4 PROCESS_HASH,
4 BYPASSED_ID_SERVICE, 1 PROCESS_RANDOM, 1 RANK_DERIVED). Two of 293's own
`id()` calls are **waived with a reason** - they are Python object identity for
an in-memory AST node used as a dict key inside one process, never written to a
file. `103_build_california_gaming.py` has four of the same shape and is NOT
waived, because it is not this pass's file to judge.

### The consolidated lint's baseline, recorded 2026-08-26

    class1  0 . class2a 0 . class2b 0 . class2c 60 . class3 0
    class4  9 . class5  6 . class6 33 . class7 74
    TOTAL (unwaived) 182 . waived 3

`docs/lint_bug_classes_baseline.json`. Previous floor was **105** over six
classes; the whole of the +77 is class 7 arriving plus the three findings named
below. `62_no_regression_check.py` tracks all nine counters as MUST_NOT_RISE and
`lint_new_defect_instances` as MUST_BE_ZERO.

**`62`'s own baseline was re-recorded at the same moment, and that needs saying
out loud.** Standing rule 15 forbids re-baselining to make a failure disappear.
This is response **(2)** in that rule - the check changed and the reason is
written into `62`'s docstring. Two facts make it safe: the gate was **GREEN
before and after** (`62` exit 0 both times), and **every metric that moved,
moved in the stricter direction** - `tier_A_ruled` 1,634 -> 1,676,
`ship_tables_shipping` 49 -> 126, `ship_dist_rows` 5,227,896 -> 7,444,208,
`ship_tables_at_zero` 205 -> 138, `tables_missing_codebook_block` 144 -> 139,
`tables_missing_notes_contract` 206 -> 139. Before this, `62`'s baseline was
recorded at 17:57, *before 293 existed*, so **every `lint_*` metric was being
printed and silently skipped** - present in the output, absent from the
comparison. They are floors now.

### THE THREE FINDINGS THAT RE-BASELINING ABSORBED - named so they are not lost

The section above this one recorded `lint_new_defect_instances = 3` as a named
gate failure. Re-recording 293's baseline to admit class 7 also absorbed those
three into the floor. They are **not fixed**, and they are named here instead of
disappearing. `lint_class4` is now pinned at **9** and `lint_class6` at **33**,
so neither can grow.

| class | script | owner / disposition |
|---|---|---|
| class4 | `215_pull_nm_revenue_sharing_quarters.py` - `RUN_DEADLINE` exits the loop, the file writes `finished`, no source-reported total is read back | **NOT MINE.** The NM/AZ gaming-regulator agent. Already named in `docs/CODE_HEALTH_AUDIT.md`. Fix: record NM's own reported quarter/document count beside what was retrieved and refuse to write `finished` when they differ |
| class4 | `217_pull_az_adg_report_archive.py` - same line, same shape | **NOT MINE.** Same agent; the file was written at 19:29 and its process (PID 3920) was live while this pass ran |
| class6 | `97_build_aliases_and_relationships.py` vs `entity_relationships.csv` | **MINE, AND BY DESIGN - see below** |

**The class6 one is mine and it is a true statement about the code.** `97` is a
full-rebuild writer of `entity_relationships.csv`;
`code/310_correct_overstated_owned_by_edge_tiers.py` is now an in-place
enricher on the same file. That is precisely the pairing class 6 detects, and it
exists because re-running `97` to pick up its own fix would have been the
rebuild/in-place collision this project has now paid for four times.

> **THE ORDERING, WRITTEN DOWN BECAUSE THE DETECTOR CANNOT INFER IT:**
> `97_build_aliases_and_relationships.py` runs FIRST and rebuilds
> `entity_relationships.csv` wholesale.
> `310_correct_overstated_owned_by_edge_tiers.py --apply` runs LAST. A
> `.bak_<date>_pre_310_correct_overstated_owned_by_edge_tiers` file beside the
> table is the signal that the enricher has touched it. After the 97 fix
> landed, a clean rebuild followed by 310 should find **0 rows to correct** -
> 310 prints exactly that and writes nothing, which is the cheapest possible
> proof that the build fix works.

---

## A RULING QUEUE MUST SUBTRACT ALREADY-RULED SUBJECTS (2026-08-26)

The owner's complaint, raised 2026-08-26: he is being re-shown entities he has
already adjudicated.

**Measured, not inferred.** `review/np_schedule_i_recipients_2026-08-12.csv`
asked him about **2,138 recipients**, and **30 of those rows carried an EIN he
had already ruled tier X** - including `UNITED WAY OF THE GREATER CHIPPEWA
VALLEY INC`, **the exact case the whole tier-inheritance rule was built on**.
Against both ruling sources the real overlap was **561 of 2,138**.

### The fix is structural, not a cleanup

`code/cedar_review_queue.py` - one shared helper, called by every review-queue
writer **before the file reaches a human**:

    import cedar_review_queue as RQ
    kept, removed, stats = RQ.subtract(rows, RQ.already_ruled())

Two sources, both read, neither optional:

- `data/clean/cedar_ruling_ledger_consolidated.csv` - 15,587 rulings
- `data/clean/cedar_identifier_ledger_final.csv` - 461 tier-X exclusions

### IT FILTERS ON `outcome`, NEVER ON `status`

`status` says the ruling was PROCESSED (`SETTLED` 14,372 /
`CONFLICT_NOT_APPLIED` 1,215). `outcome` says what it DECIDED. Filtering on
`status == SETTLED` is the trap this project paid for twice in one day - one
ruling read SETTLED while its outcome was `HOLD_OVER_OWNER`, *"HOLD -
RETRACTION REQUIRED"*. Three groups, and the policy is written where it can be
argued with:

| group | outcomes | what happens |
|---|---|---|
| **ADJUDICATED** | `ENTITY`, `NEGATIVE`, `CLASS`, `HOLD`, `HOLD_OVER_OWNER`, `UNRESOLVED_ENTITY`, plus ledger tier X | **REMOVED**, with the row and the deciding ruling written out in full |
| **CONFLICTED** | `POSITIVE_VS_NOT_NATIVE`, `TWO_DIFFERENT_UNRESOLVED_OWNERS`, `OWNER_VS_DIFFERENT_UNRESOLVED_OWNER`, `TWO_DIFFERENT_CLASSES`, `CLASS_CONTRADICTS_OWNER_SPINE_CLASS` | **KEPT and ANNOTATED.** A tie needs a human - but the card now says *"you have ruled this twice and they disagree"* instead of asking as though it were new. Subtracting them would hide a contradiction |
| **UNKNOWN** | anything else | **KEPT and NAMED.** A new outcome vocabulary must be visible the day it lands |

**`HOLD` is deliberately ADJUDICATED.** `173_consolidate_rulings_ledger.py`
says so in its own docstring: *"HOLD / BLOCKED are DECISIONS, not absences. They
are written as an explicit status **so the subject stops re-entering the
queue**."* A queue that re-asks a HOLD has read a decision as a silence.

### The four safety rules, each one earned

1. **A row that already carries an ANSWER is never removed.** `review/` is not
   only a queue directory - it is the **ruling corpus**, and
   `173_consolidate_rulings_ledger.py` discovers its verdicts by walking
   `review/**.csv` for a ruling column. Deleting an answered row would delete a
   ruling. Only rows whose answer column is BLANK are eligible, so 173's input
   is bit-for-bit unchanged for every verdict it reads.
2. **Hand inboxes and 173's own outputs are never touched** - `rulings_inbox_*`,
   `_decisions_*`, `cedar_ruling_*`, `ruling_conflicts_*`. The exclusion list is
   IMPORTED from 173, not copied.
3. **A file another agent is writing is NAMED, not edited** (mtime under 30
   minutes). Four were skipped on this run under concurrency rule 6.
4. **Every dropped row is written out in full, with the reason**, to
   `review/_already_ruled_removals/`. Columns 173 would read as a ruling are
   prefixed `queued_` there, so an audit file can never be swept back in as
   evidence for itself.

### What it removed, applied by `code/309_apply_already_ruled_filter_to_review_queues.py`

**34 queue files rewritten. 36,815 rows in -> 10,190 removed -> 26,625 kept, 46
annotated as CONFLICTED.** Backups tagged
`.bak_2026-08-26_pre_309_apply_already_ruled_filter_to_review_queues`; every
file re-read from disk afterwards.

| by outcome | rows |
|---|--:|
| ENTITY | 5,180 |
| NEGATIVE | 1,979 |
| CLASS | 1,597 |
| HOLD | 632 |
| UNRESOLVED_ENTITY | 434 |
| HOLD_OVER_OWNER | 361 |
| ledger tier X | 7 |

The heaviest files: `MASTER_QUEUE_2026-08-07.csv` 10,859 -> 6,559 (**4,300**),
`review_queue_2026-08-05.csv` 4,813 -> 3,232 (1,581),
`contract_spiderweb_candidates_2026-08-06.csv` 714 -> 27 (687),
`np_schedule_i_recipients_2026-08-12.csv` 2,138 -> **1,577** (561),
`np_placename_risk_2026-08-05.csv` 412 -> 15 (397),
`lobbying_ambiguous_2026-08-05.csv` 361 -> 5 (356).

**Verified after the write:** UNITED WAY OF THE GREATER CHIPPEWA VALLEY is gone
and **0 of the 30 tier-X EINs remain** in the Schedule I queue. The nine other
`CHIPPEWA VALLEY` names still there are different EINs that have never been
ruled, which is correct - the subtraction is on the identifier, never on a name
when an identifier is present.

### And it is wired into the writer, not only applied once

`129_build_review_queue.py` now calls the helper before it writes
`data/interim/review_queue.json`, and prints the drop with the outcomes and the
first few subjects by name. On its first run with the filter: **510 -> 380
items, 130 removed** - *on top of* the input files already having been filtered.
`RED LAKE NATION COLLEGE`, `Santa Fe Indian School`, `Alaska Federation of
Natives`, `Department of Hawaiian Homelands` and `California Rural Indian
Health Board` were all being re-asked.

**THE RULE: a queue writer that does not subtract the ledger is asking the
owner to do work he has already done.** Call `cedar_review_queue.subtract()`
before you write the file, every time.

---

## 169 STILL NOT RE-RUN, RE-CHECKED 2026-08-26 ~20:00 - ONE BLOCKER LEFT

The earlier section "169 WAS NOT RE-RUN, AND WHY" named two blockers. **One has
cleared and one has not.**

| input | writer | state at 20:00 |
|---|---|---|
| `cedar_identifier_ledger_final.csv`, `cedar_entity_spine.csv` | the individual-Native-firm agent (`241`, `244`) | **process gone** - but both files were re-written at **19:22**, after that agent's 19:04 finish, so something else touched them too |
| `data/clean/subawards.csv` | **`121_pull_subawards_api.py pull --sequential`** | **STILL LIVE.** Wrapper PID **8404** and poller PID **13736**, both present in `Win32_Process`, started 17:19:08 |

**A DEAD WRAPPER IS NOT A DEAD POLLER, and neither is a stale lock.** All three
checks were made and all three agree:

1. `py.exe -3 code/121_pull_subawards_api.py pull --sequential` - PID 8404, alive
2. `python.exe code/121_pull_subawards_api.py pull --sequential` - PID 13736, alive
3. `logs/_HOSTLOCK_api.usaspending.gov.json` - held by **PID 13736**, claimed
   `2026-08-26T21:19:08Z`, `collect_deadline_utc` **2026-08-27T05:19:08Z**, five
   jobs in flight (fy2021-fy2024 + fy2020_procurement)

`subawards.csv` is one of 169's four `SPEND_FILES`. **A graph built from a table
another agent is still appending is a snapshot of an inconsistent moment, and
115,471 graph nodes is exactly the artefact a later reader quotes as settled.**
So 169 was **NOT run**, and this is the second session to record that decision
rather than the run.

**Everything else it needs is ready.** Its two polarity defects are fixed
(above), it takes no arguments, makes no network call, and its inputs already
carry every write from today. When 121 has exited - verify with
`Win32_Process.CommandLine`, never with `ps` - one command finishes it:

    py -3 code/169_build_identifier_graph.py

Expect **no change** in the ruled-Native EIN count from the polarity fix (89
before, 89 after, measured); what changes is the 3,883 ANCSA attributions and
the spine's growth 1,489 -> 1,534 flowing into the graph.


### ADDENDUM, same session: a second pass caught 3 more files, and one file it must NEVER touch

Four files were skipped on the first pass under concurrency rule 6 (mtime under
30 minutes). Once their agents had exited, a second `--apply` took three of
them: `individual_native_ownership_ambiguous_2026-08-26.csv` 97 -> 60 (37),
`missing_entity_attribution_2026-08-26.csv` 66 -> 59 (7),
`nigc_declination_entities_held_2026-08-06.csv` 106 -> 100 (6).

**Session total: 37 queue files, 10,240 already-ruled rows subtracted.**

The fourth was REFUSED, and the reason is now a rule in the code.
`individual_native_queue_withdrawn_already_ruled_2026-08-26.csv` is another
agent's own audit of what IT withdrew for being already ruled - it has a
`YOUR_RULING` column, so it looked exactly like a queue, and the filter would
have emptied it to zero rows. **Subtracting already-ruled rows from a file whose
entire content IS already-ruled rows deletes the evidence that the withdrawal
happened. A RECORD OF A DROP IS NOT A QUESTION.** `309` now skips any filename
matching `already_ruled|withdrawn|_removals?_|_removed_|_applied_|_audit_|_log_`
and prints why.

---

## NAMED GATE FAILURE - `lint_class7`, owner identified (2026-08-26 ~19:58)

Recorded under standing rule 15 option 3, which requires naming the failing
metric, the owning file and what has to happen - not writing "pre-existing, not
mine" and continuing. **The gate is RED on exactly one finding, and it is not
this pass's.**

```
lint_new_defect_instances = 1, must be 0
lint_class7               ROSE 74 -> 75
lint_bug_class_instances  ROSE 182 -> 183
```

All three lines are the SAME single finding:

    class7  320_stage_tribal_certification_facts.py
            f"TCF-{CAPTURE_DATE.replace('-', '')}-{i:04d}"

**`certification_fact_id` is POSITIONAL** - `{i:04d}` is the row's index in an
iteration, so every id below an inserted row shifts on the next run. That is the
`EMP-OSHATRIBE-*` shape exactly: 482 of 492 rows changed id on a re-run, and
re-running the merge would have appended 492 silent duplicates.

**OWNER: the tribal-vendor-list agent.** `code/320_stage_tribal_certification_
facts.py` was written at **19:55:27**, about three minutes before the gate ran,
alongside `316`, `317`, `318`, `319` (19:46-19:57) - and alongside
`code/326_triage_class7_key_risk.py` (19:49), which is that agent's OWN class-7
triage. This is in-flight work by an agent already working this exact class.

**WHAT HAS TO HAPPEN:** make the id a function of the ROW rather than of its
position - `cedar_keys.stable_digest` over
`(certifying_authority_entity_id, certification_source_id, <subject>)`, or
`cedar_ids.allocate`, which takes the file lock. One line. Then
`py -3 code/293_lint_bug_classes.py --baseline`.

**IT WAS NOT RE-BASELINED AWAY, DELIBERATELY.** 293's baseline was recorded at
~19:52 with class7 = 74; this instance landed after it. Re-recording again to
swallow another agent's three-minute-old defect is precisely what standing rule
15 forbids, and it is how a gate becomes a decoration. The FLOOR is correct; the
finding is real; it belongs to a named owner who is already in that file.

**Everything else in the gate is GREEN and was green immediately before this
landed** - `62` exited 0 at ~19:52 on the same baselines. The three trap metrics
are 0, `lint_class1/2a/2b/3` are 0, and `lint_new_defect_instances` was 0.

**A message bug was fixed while reading this failure.** `62` appended the
RULINGS explanation - *"A ruling that is not applied back to its source table is
not a ruling, it is a note"* - to every `lint_*` MUST_NOT_RISE failure, because
that branch was the `else`. **A failure message that explains the wrong defect
sends the next agent to the wrong file.** `lint_*` now gets its own text,
naming the waiver syntax and saying explicitly not to re-baseline.

### CLOSED 19:59:15, four minutes after being named. GATE IS GREEN.

The owning agent fixed it. `certification_fact_id` is now

    f"TCF-{tid}-{f['identifier_type']}-{f['identifier']}"

- a function of the ROW (the certifying authority and the identifier the fact is
about) instead of the row's POSITION in an iteration. No re-baseline was needed
by anyone.

    lint_class7               75 -> 74
    lint_bug_class_instances 183 -> 182
    lint_new_defect_instances  1 -> 0
    62_no_regression_check.py  exit 0, "no regressions"

**This is the whole argument for the class, on its first day.** A positional
primary key produces no error, no warning and a perfectly unique column; the
only thing that would ever have exposed it is a check that looks at how the id
is MADE. It was written at 19:55, detected at 19:58, named at 19:58 and fixed at
19:59 - against a defect of the same shape (`EMP-OSHATRIBE-*`) that sat
undetected until a re-run changed 482 of 492 ids.

---

## WAYBACK IS NOT A ROUTE AROUND A LOGIN (2026-08-26, script 317)

Earned in the tribal vendor-list feasibility study
(`docs/TRIBAL_VENDOR_LISTS_FEASIBILITY.md`, scripts `316`–`322`).

Choctaw Nation's live Commerce page links a preferred-supplier portal for
"qualified Choctaw tribal member-owned business enterprises". The host is
**NXDOMAIN on two independent resolvers**, so it read as a broken link on a
live government page and was queued as the highest-value archive recovery in
the lower 48 — a certification list that might exist only in Wayback.

The CDX enumeration answered it in one query: **527 archived URLs,
2014-08-23 to 2025-05-24**, whose 2023-07-07 capture lists
`/api/account/register`, `/api/account/resetpassword`,
`/api/account/userinfo` beside `/api/suppliers`, `/api/supplierprofile/`,
`/api/owners` and `/api/ownershiproles`.

**It was a registered-account application, not a published list.** The archive
holds the ROUTE NAMES; the payload was gated.

> **`LIST_BEHIND_LOGIN` means stop, and it means stop in the archive too.** A
> directory a tribe put behind an account is not ours to take from an archive
> either. The same rule now applies to a stated robots refusal:
> `elyshoshonetribe.com` names `ClaudeBot` and `anthropic-ai` under an explicit
> Disallow, so it is `wayback_priority = EXCLUDED` — **an origin's refusal of
> this agent is not routed around by fetching the same content from a mirror.**
> `code/317` enforces both by refusing to sweep any registry row marked
> EXCLUDED, and it NAMES what it dropped rather than counting it.

**Dated strictly, as the standing rule requires.** The account gate is what
the 2023-07-07 capture shows. A 2014-08-23 capture returns 200 on the root and
its state is UNKNOWN. **A 2023 snapshot cannot testify about 2014 any more
than it can about 2026.**

**And the cheap probe paid for itself.** One CDX query converted a promising
target into a closed one before anybody spent a day on it — the same shape as
the SAM canary and the two-day subaward job.

### Three more traps from the same study, worth more than the study

1. **"TERO" IS THE WRONG SEARCH TERM.** CSKT calls it the *Indian Preference
   Office*; CTUIR buries it under Workforce Development; Navajo runs it as the
   *Business Regulatory Department*; Cherokee, EBCI and MHA run it on
   **separate domains** (`cherokeetero.com`, `ebci-tero.com`, `mhatero.com`)
   barely linked from the tribal site. **A keyword sweep on "TERO" alone finds
   3 of 13.** Synonym set: TERO · Tribal Employment Rights · Indian Preference ·
   Indian-Owned Business · Business Regulatory · Preferred Supplier · Certified
   Contractor · Source List.
2. **BEING ON A CERTIFIED LIST IS NOT BY ITSELF AN OWNERSHIP CLAIM.** Colville's
   TERO file flags firms `Certified Title 10 = Yes` at **0% Indian ownership**.
   The percentage column must be read. Same shape as the tier rule: the
   exactness of the FLAG says nothing about what it asserts.
3. **`oglalalakotanation.net` IS AN OFFSHORE ONLINE CASINO IMPERSONATING THE
   TRIBE**, served through a Cloudflare Workers subdomain. It must never enter
   a host list or be cited as tribal. The legitimate host is `oglala.gov`.
   Akwesasne material online frequently belongs to the **Mohawk Council of
   Akwesasne (Canada)** — a different government.

### A THIRD PROVENANCE RESTRICTION IS NOW MACHINERY

`cedar_codebook.TRIBAL_SOURCE_RESTRICTED_FILES` sits beside
`LICENSED_SOURCE_FILES`, and `code/321_gate_tribal_source_restriction.py`
(with a seven-case `--selftest`) fails a build on: a restricted file missing
its consent columns; an unrecognised `consent_status`; `publishable = Y`
without `OPT_IN`; an `OPT_OUT` that did not suppress; and a restricted file
reaching `data/clean/` or `dist/`.

**A federal record is public by statute. A sovereign government's own
publication is not the same thing, and "publicly reachable" is not "licensed
for commercial redistribution." SILENCE IS UNRESOLVED, NEVER PERMISSION.**
Removal is one field — and so is admission, because some TERO offices will
want the reach and saying yes must be as cheap as saying no.

### CORROBORATION of the named `lint_new_defect_instances` failure (23:5x)

The gate failure named above at ~19:45 is **still owned by live agents, and
one of them was confirmed running**: `code/217_pull_az_adg_report_archive.py`
was alive as PID 3920/15464 during this session, alongside
`121_pull_subawards_api.py`, `227_anomaly_sweep.py` and
`284_audit_nondeterministic_keys.py`. Nothing in `316`–`322` contributes to
it — all seven scripts lint clean against every class, verified by grepping
293's own output for their filenames — and one class-7 instance that WAS ours
(a positional `certification_fact_id`) was **fixed rather than waived**, keyed
on (authority, identifier type, identifier) instead of an `enumerate()`
counter.

---

## NAMED GATE FAILURE — the lobbying correction pass, owner identified (2026-08-26 ~20:1x)

Per standing rule 15 option 3, named before continuing.
`code/62_no_regression_check.py` FAILS on **six** metrics, all one event:

    ship_dist_rows FELL 7,444,230 -> 7,444,176            (-54)
    ship_tables_at_zero ROSE 138 -> 139
    tables_missing_codebook_block ROSE 139 -> 140
    tables_missing_from_25_TABLES ROSE 234 -> 235
    tables_missing_from_27_SPEC ROSE 249 -> 250
    tables_missing_notes_contract ROSE 139 -> 140
    ship_ratio_pct FELL 92.559% -> 92.547% AND shipped rows fell too

**OWNER: the agent writing `code/350`–`code/354`, the lobbying/FOIA correction
pass.** `data/clean/cedar_correction_register.csv` (19 rows) landed at **20:08**
and is written by **`code/354_correction_register.py`** (20:05), beside
`350_withdraw_false_lobbying_attributions.py` (20:07),
`351_rebuild_lobbying_panel_from_corrected_disclosures.py` (20:08) and
`352_unlink_false_foia_entity_links.py` (20:09). All four are in-flight work
written after `62` recorded the 19:4x baseline.

**All five "ROSE" metrics are the SAME new table** — `cedar_correction_register`
is unregistered in the codebook master, `25_TABLES`, `27_SPEC` and the notes
contract, so it trips four registration counters and the zero-ship counter at
once. One task, five lines.

**The `ship_dist_rows` fall of 54 is CORRECT and not lost shipping, and the
gate's own per-table baseline proves it.** A later run named the table
exactly:

    A TABLE THAT WAS SHIPPING STOPPED SHIPPING -
    tribe_year_lobbying_panel.csv: 5,051 -> 4,997

**-54, the whole fall, on one table** — and that table is the output of
`351_rebuild_lobbying_panel_from_corrected_disclosures.py`, which rebuilds the
panel after `350_withdraw_false_lobbying_attributions.py` withdraws false
attributions. **A withdrawal REMOVES rows by design.** The gate cannot tell a
correction from a loss, and `ship_ratio_pct` fires its hard case because
shipped rows fell alongside the ratio.

This is exactly what the per-table `dist` baseline was added for: a scalar
would have said only "the total moved". Worth recording as a success of that
design, not just as a failure of this run.

**WHAT HAS TO HAPPEN, by the owner:** register
`cedar_correction_register.csv` (codebook block, then `87` → `25` → `27` per
`docs/SHIPPING_RUNBOOK.md`), which clears five of the six lines; and record in
the correction pass's own log that the 54-row `dist` fall is a **withdrawal,
with the withdrawn rows named**, so the next reader can tell a correction from
a regression. A row count that falls with no attributed cause is how a
correction gets re-litigated as a bug.

**NOT the tribal vendor-list study (`316`–`322`).** Those seven scripts write
only to `review/`, `docs/`, `docs/codebooks/` and
`data/staging/tribal_vendor_lists/` — **nothing to `data/clean/` or `dist/`,
by design, because `321_gate_tribal_source_restriction.py` fails the build if a
tribal-source file reaches either.** Verified by grepping 293's output for all
seven filenames: zero findings across every class.

**Improved in the same run, and worth recording:** `lint_new_defect_instances`
went **3 → 0** — the `215`/`217` class-4 and `97` class-6 instances named at
~19:45 were resolved by their owners. `lint_bug_class_instances` fell 182 → 165
and `lint_class7` fell 74 → 57.

---

## NAMED GATE FAILURE — the correction register, owner identified (2026-08-26 ~20:15)

Recorded by the CourtListener/RECAP adjudication pass (`code/366`–`373`) per
standing rule 15 option 3, **before** it did any work. `62_no_regression_check.py`
exits **1** on this machine right now and **not one line of it is this pass's**.

| failing metric | movement | owner |
|---|---|---|
| `ship_tables_at_zero` | 138 → 139 | `code/354_correction_register.py` |
| `tables_missing_codebook_block` | 139 → 140 | ” |
| `tables_missing_from_25_TABLES` | 234 → 235 | ” |
| `tables_missing_from_27_SPEC` | 249 → 250 | ” |
| `tables_missing_notes_contract` | 139 → 140 | ” |
| `ship_dist_rows` | 7,444,230 → 7,444,176 (**−54**) | `code/351_rebuild_lobbying_panel_from_corrected_disclosures.py` |
| `ship_ratio_pct` | 92.559% → 92.547% | consequence of the −54 |

**Both are the same live build, minutes old.** `code/350`, `351`, `352` and
`354` carry mtimes 20:05–20:09 on 2026-08-26.

- The five registry metrics are **one new table**, `data/clean/cedar_correction_register.csv`
  (19 rows), landing from `354` and not yet given a codebook block. The gate
  names the fix itself: register the block, then re-run `87` → `25` → `27` per
  `docs/SHIPPING_RUNBOOK.md`.
- The **−54 is exactly the declared withdrawal**, not lost shipping. `351`'s own
  docstring states it: *"5,051 -> 4,997 rows. 54 (entity, year) cells cease to
  exist because every filing in them was withdrawn - 18 by script 65
  (2026-08-06, never propagated to here) and 36 by script 350. … That fall is
  DECLARED in `data/clean/cedar_correction_register.csv` with an exact
  `rows_removed`, which is what lets `62_no_regression_check.py` tell this
  withdrawal from lost shipping instead of failing on it."*

**So the withdrawal declaration exists and the gate is not reading it.** That is
the actionable half of this note: `62` fails on the −54 anyway, which means the
`rows_removed` route `351` relies on is either unwired or not consulted by the
`ship_dist_rows` comparison. Whoever owns `350`–`354` should close that loop —
a declaration a gate cannot see is the same shape as a ruling that is never
applied.

**What this pass did instead of stepping around it:** named it here, then
touched **no shipping table, no codebook, no registry and no shared table at
all** — every output staged to `review/`. `293_lint_bug_classes.py` was run
before and after and reported `lint_new_defect_instances = 0` both times.

---

## NAMED GATE FAILURE — a new unregistered table, owner identified (2026-08-26 ~20:15)

Per standing rule 15 option 3, recorded **before** the SAM FY2000–2007
five-variant load (`code/163_load_sam_contract_awards.py`, this pass) ran.
`62_no_regression_check.py` FAILED on six coupled shipping metrics, all of them
naming **one** cause:

    NEW TABLES AT A 0% SHIP RATIO (1): cedar_correction_register.csv (24 rows)
    ship_tables_at_zero            138 -> 139
    tables_missing_codebook_block  139 -> 140
    tables_missing_from_25_TABLES  234 -> 235
    tables_missing_from_27_SPEC    249 -> 250
    tables_missing_notes_contract  139 -> 140
    ship_dist_rows           7,444,230 -> 7,444,176   (-54)
    ship_ratio_pct              92.559 -> 92.547

**OWNER: the corrections agent working `code/350`–`code/354`.**
`data/clean/cedar_correction_register.csv` was written at **20:09**, six minutes
before this gate run, by `code/354_correction_register.py`, and is appended to
by `350_withdraw_false_lobbying_attributions.py`,
`351_rebuild_lobbying_panel_from_corrected_disclosures.py` and
`352_unlink_false_foia_entity_links.py`. That is **live work, not abandoned
work**; registering another agent's table mid-run would race its author.

**WHAT HAS TO HAPPEN:** register a codebook block for
`cedar_correction_register.csv`, then re-run `the full 7-step ship chain (`py -3 code/build.py ship`; “87 → 25 → 27” is a 3-step shorthand that omits the codebook build, the gate, the coverage profile and the harmonised views)` per
`docs/SHIPPING_RUNBOOK.md`. The `ship_dist_rows` fall of 54 rows is the same
agent's lobbying-panel rebuild (`351`) and is **declared** in that register.

**What this pass did instead of stepping around it:** named it here, and wrote
**nothing to `data/clean` that was not already an existing SAM table**. The SAM
load rewrites four existing paths in place
(`sam_prime_contracts_fy2000_2007*.csv`, its manifest and its codebook
fragment); every NEW artefact of this pass went to `review/`, so none of the six
failing counters can move because of it.

### AFTER the SAM load, same evening — re-run, and what changed

The **same six counters fail by the same deltas**, so none of them is the SAM
load's. Two lines moved and both are accounted for here:

- **`lint_class2c` 60 -> 61 and `lint_new_defect_instances` 0 -> 1.** The new
  instance is **`353_propagate_lobbying_corrections_to_consumers.py`:
  `unmatched += 1`** — a drop counter that does not NAME what it dropped.
  **Same owner as `cedar_correction_register.csv`**, the 350–354 corrections
  agent. `293_lint_bug_classes.py` output was grepped for `163_load_sam` and
  `358_measure_sam`: **no hits, both clean.**
- **`tribe_year_lobbying_panel.csv` 5,051 -> 4,997 rows.** Also the 350–354
  agent — it is `351_rebuild_lobbying_panel_from_corrected_disclosures.py`'s
  declared fall, recorded in that agent's own correction register.

**One line the SAM load DID move, and it is not a failure:**
`ship_ratio_pct` 92.559% -> 86.915%, which `62` itself files under *"READ THESE
— measured, not failed"* because **shipped rows ROSE** (7,444,230 ->
7,445,042). The cause is named in its own output: the SAM table went
**8,273 -> 269,312 rows** and is unregistered, so it added ~261k rows to the
warehouse and none to the shelf. **It was unregistered before this pass too** —
`ship_tables_at_zero` did not rise on its account. Registering it needs
`the full 7-step ship chain (`py -3 code/build.py ship`; “87 → 25 → 27” is a 3-step shorthand that omits the codebook build, the gate, the coverage profile and the harmonised views)` per `docs/SHIPPING_RUNBOOK.md`, which is exactly the sequence
the corrections agent above must run for its own table, and `41_build_codebooks.py`
is on the do-not-run list. **Left for that run rather than raced.**

---

## CLASS 7 CUT FROM 74 TO 42 — POSITIONAL AND PROCESS-HASH KEYS (2026-08-26, scripts 326–328)

**Full write-up, including the triage of all 76 findings and the blocked list
with its consumers: `docs/CLASS7_KEY_MIGRATION_LOG.md`. Read it before touching
any `*_id` column.**

`class7` was the largest class the linter finds and the blocker on loading any
of this into a database — a key that changes on every rebuild makes an
integrated, updatable dataset impossible.

### THE RULE, NOW IMPLEMENTED RATHER THAN ASSERTED

> A primary key is either a **NATURAL key stated by the source**, or a
> **deterministic digest of stated columns**. Never a position. Never `hash()`.

`cedar_keys.surrogate_id(prefix, row, columns)` — blake2b over normalised,
stated fields. **Every migrated key names its composing columns in a
`*_KEY_COLUMNS` constant beside the definition**, with a comment saying why
those columns, and `328_audit_id_service_bypass.py` checks that constant against
the migration spec on every run. That check is what stops the producer and the
migrated data drifting apart, which would silently re-key the table on the next
rebuild.

### TRIAGE BY RISK, NOT BY COUNT — `326_triage_class7_key_risk.py`

76 findings: **12 HIGH · 25 MEDIUM · 39 LOW**, ruled on evidence — a full value
scan for the minted prefix across every clean and spine table, plus a grep for
every consuming script — not on the finding text.

**One band exists because a measurement was impossible, and it is NOT "low".**
An f-string beginning with a formatted value (`f"{did}-E{n:02d}"`) has no
literal prefix, so nothing can be searched for. Those report as
**UNTRACEABLE / `NO_LITERAL_PREFIX_TO_TRACE`**. Printing them as LOW would be
the 102 defect in a new costume: an absent measurement rendered as a zero.

### 11 CONVERTED, 7 BLOCKED-ON-CONSUMERS — `327_migrate_class7_keys_to_digests.py`

Converted in place, producers edited to match: `ferc_filing_id` (102,615 rows),
`earmark_id` (1,002 — including a second `abs(hash())` nobody had recorded),
`consultation_event_id` (1,363), `anc_id` (196 plus 19,309 foreign-key
references in two other tables), `party_id`, `fact_id`, `allocation_id`,
`band_id`, `observation_id` (admin), and both `event_id`s.

**THE MIGRATION IS THE HARD PART AND IT IS ENFORCED.** 327 does a FULL scan of
every `data/clean/**/*.csv` and `data/spine/*.csv`, cell by cell, including
inside `,`/`;`/`|` lists, before writing anything. Declared locations migrate;
**one undeclared location aborts the whole spec** and it is reported as
BLOCKED-ON-CONSUMERS with the location named. A half-migrated key is worse than
a bad key — the bad key at least fails uniformly.

Blocked, with consumers listed in the log: `verification_id` (**live agent** —
170/171 and 241–244 were written this evening; the fix is already specified in
`cedar_keys.PRIVACY_SURROGATE`), `exclusion_id` and `nho_id` (both cited **by
value in hand-authored rulings** in `data/spine/cedar_rulings.csv`),
`cedar_opinion_id`, the `83_build_resource_ledger.py` family, `ordinance_id`,
and `RV-` (producer is NEVER-RUN).

### THREE THINGS THIS TURNED UP THAT NOBODY HAD WRITTEN DOWN

**1. `ferc_docket_filings.csv` HAS 989 DUPLICATE ROWS, AND THE PROCESS HASH WAS
HIDING THEM.** The new deterministic key is **not unique**: 769 groups covering
1,758 rows. Every one of those rows is identical to its twin on *every other
column of the table* up to case and whitespace — the same eLibrary document
recorded twice. The old `abs(hash())` id was masking that behind 855 collisions
of its own. The column is now a stable CONTENT identity and the table stays
**BLOCKED for a primary key**. Do not make it a foreign-key target.

**2. A LENGTH CAP ON A DELIMITED LIST MUST CUT AT A DELIMITER.**
`133_build_ferc_advocacy.py` wrote `";".join(ids)[:400]`, which sliced mid-id:
docket P-001 carried a cross-reference reading **`S1`** — half of an id,
pointing at nothing, and indistinguishable from a real reference. Found by
re-reading the migrated file rather than trusting the run log. `_cap_list` now
drops WHOLE ids and says how many it dropped; the live cell was repaired and the
column now has 0 dangling references.

**Same class, caught the same way, and worth its own rule: a migration that
re-joins a list cell must PRESERVE THE PRODUCER'S SEPARATOR.** 327's first pass
re-joined `section_106_cross_ref` with `" | "` where 133 writes `";"`, leaving
the live file holding a delimiter no rebuild produces and no reader splits on.
Fixed in 327; the file was rebuilt from its backup and re-verified.

**3. SIX `CEDAR-ADMREG` ID BLOCKS WERE MINTED BY F-STRING AND THE ID SERVICE
KNEW ABOUT ONE.** `84_build_nigc_regions.py` and
`85_build_admin_region_crosswalk.py` each pre-assigned contiguous ranges in a
comment; `cedar_ids.RESERVED_BLOCKS` listed only one of the six, so
`allocate("CEDAR-ADMREG")` could have walked straight into `BIA_REGION`.
`cedar_ids.declare_static_block(prefix, lo, hi, owner, why)` now registers a
block, **refuses an overlap with a different owner**, and `allocate` steps over
all of them. A static block is a legitimate bypass; an **undeclared** one is
not, and `328` is the check that tells them apart — it tests for a DECLARATION,
where 284's rule was only that the file mentions `cedar_ids` anywhere.

### A FIXTURE THAT DIES WHEN THE BUG IS FIXED IS A FIXTURE THAT WILL BE DELETED

`284_audit_nondeterministic_keys.py`'s self-test asserted that the lint could
still find the defect **in three named real scripts**. The moment
`ferc_filing_id` was repaired it reported **"FIXTURE SELF-TEST FAILED — class 7
must NOT be trusted"** on a run where the class had just improved by 32.

That pressure points exactly the wrong way: the cheapest ways to make it green
again are to re-introduce the bug or delete the fixture. The self-test now runs
against **`SYNTHETIC_FIXTURES`** — each defect reduced to its smallest form, so
it cannot be fixed out from under the detector — and `FIXTURES` keeps the three
measured real instances as the historical record, each with `fixed_on` and what
replaced it. A real instance that vanishes with **nothing recording it as
fixed** still fails.

> **A regression test must fail when the code gets worse and pass when it gets
> better. Pin it to the DEFECT SHAPE, never to a line number in a file you
> intend to repair.**

### GATE STATE

`293_lint_bug_classes.py` before/after: **class7 74 → 42**; `class2c` 60,
`class4` 9, `class5` 6, `class6` 33, `class1/2a/2b/3` 0 — **no class rose**,
`lint_new_defect_instances = 0`, total 182 → 150. `--selftest` passes. 16
waivers, each with a reason on the line: 13 × `id(obj)` object identity
(103, 84, 85, 99), 1 × a `uuid4` **multipart form boundary** in 143, and the 2
pre-existing in 293.

`62_no_regression_check.py`: the three trap metrics
(`files_with_columns_lost_vs_backup`, `units_short_of_source_reported_total`,
`coverage_columns_that_do_not_exist`) are all **0** and `ship_dist_rows` rose
7,444,230 → 7,445,042. It still FAILS on the five registry metrics and on
`tribe_year_lobbying_panel.csv` 5,051 → 4,997 — **already named three times in
this file** by the agent running the lobbying/FOIA correction pass
(`350`–`354`, written 20:14–20:15; `cedar_correction_register.csv` needs its
codebook block, then `the full 7-step ship chain (`py -3 code/build.py ship`; “87 → 25 → 27” is a 3-step shorthand that omits the codebook build, the gate, the coverage profile and the harmonised views)`). **None of it is this pass's**: the key
migration touched 13 already-registered tables, created nothing in `data/clean`,
and dropped no row from any of them.

**LEFT FOR THEIR OWNERS, both LOW risk, both named rather than edited because
the files were live while this ran:** `227_anomaly_sweep.py:1038`
(`hash(tuple(...))` for within-run duplicate detection — the process was
*running*) and `171_build_individual_native_verification.py:486`
(`used_web.add(id(w))`, object identity). Each wants a one-line
`# lint-ok: class7 - …` waiver from whoever owns it.

**Recorded at 20:40, immediately after that re-baseline:** `293` now reports
`class2c ROSE 60 -> 61`, and the new finding is
`353_propagate_lobbying_corrections_to_consumers.py: unmatched += 1` — a file
that did not exist when the baseline was taken. **Same owner as the gate
failure above** (the lobbying/FOIA correction pass, scripts 350–358). `class7`
is unchanged at 42. WHAT HAS TO HAPPEN: name what `unmatched` dropped, in the
same block — a count scrolls past, a filename is a task — or waive the line
with a reason.

### CORROBORATION 2026-08-26, later — the gaming property-site re-mine pass (`382`–`386`)

Ran `62` and `293` **before** touching anything. Every failing line is already
named above and **not one of them is this pass's**:

    lint_new_defect_instances = 1   -> 353_propagate_lobbying_corrections_to_consumers.py (class2c)
    lint_class2c            60 -> 61  same
    ship_tables_at_zero    138 -> 139 |
    tables_missing_codebook_block 139 -> 140 |
    tables_missing_from_25_TABLES 234 -> 235 |  all one table:
    tables_missing_from_27_SPEC   249 -> 250 |  cedar_correction_register.csv (163 rows)
    tables_missing_notes_contract 139 -> 140 |  from 354_correction_register.py
    tribe_year_lobbying_panel.csv 5,051 -> 4,997  -> 351, the declared withdrawal

Mtimes confirm the owner: `code/350` 20:14, `351` 20:15, `353` **20:24**,
`354` 20:14; `cedar_correction_register.csv` 20:24;
`tribe_year_lobbying_panel.csv` 20:15. `353` is **nine minutes newer** than the
`~20:15` write-ups above, which is why its class2c instance appears here and not
in them.

**What this pass did instead of stepping around it:** wrote **no new
`data/clean/` table**, so none of the five registration counters can move
because of it; staged every new artefact to `data/staging/` and `review/`;
enriched `cedar_domain.py` only (no data file). `293` re-run after: unchanged.

---

## THE THREE FALSE ATTRIBUTIONS WERE FIXED AT THE SHIPPING TABLE (2026-08-26, ~20:15–21:00)

Scripts **350–356**. Owner of everything in this section.

### The failures named against this pass above are now CLEARED

The two write-ups immediately above correctly identified this pass as the owner
of six failing gate lines. All six are fixed, and here is how, so the next
reader does not re-open them:

| line | disposition |
|---|---|
| `lint_class2c` 60 → 61, `lint_new_defect_instances` = 1 | **FIXED.** `353`'s `unmatched += 1` now appends the `filing_uuid` and prints every one of them. A count scrolls past; a key is a task. |
| `ship_tables_at_zero`, `tables_missing_codebook_block`, `..._from_25_TABLES`, `..._from_27_SPEC`, `..._notes_contract` all +1 | **FIXED** by `code/356_register_correction_register.py`, following `183`'s pattern exactly: a codebook FRAGMENT (the master is never written), a notes contract in `dist/00_reference/` built from `87`'s own blocks, and hand edits to `TABLES` in `25` and `SPEC` in `27`. `355` then created the table in `dist/cedar_press.db` — a notes contract asserting 163 shipped rows while the database has none is a false claim. |
| `tribe_year_lobbying_panel.csv` 5,051 → 4,997 | **NOT A REGRESSION, and the gate now says so itself.** See the allowance below. |

**The only failing line left in `62`/`293` belongs to another pass and is named
here per rule 15 option 3:**

    lint_class2c  ROSE 60 -> 61
    code/382_remine_property_site_corpus.py:  stats["capacity_refused_implausible"] += 1

**Owner: the gaming property-site re-mine pass (382–386).** WHAT HAS TO HAPPEN:
name what was refused — the site, the capacity, the reason — beside the counter,
or waive the line with a reason. It is defect class 2c and it is the same shape
that hid 33,817 rows for twenty days.

### THE RULE THIS PASS EARNED

> **A CORRECTION THAT REACHED ONE TABLE AND NOT ITS SIBLINGS IS THE SAME
> DISEASE AS A RULING THAT REACHED NONE.**

`rulings_unapplied` (1,215) catches a ruling that reached NO table. It reported
nothing about the three false attributions that were live in shipping tables
this morning — **correctly**, because from its point of view every one of them
HAD been applied. They had been applied to exactly one file each:

- **FA-01.** `65_lobbying_organization_type_guard.py` withdrew SALT RIVER
  PROJECT from `native_entity_lobbying_disclosures.csv` at 2026-08-06 16:19.
  `tribe_year_lobbying_panel.csv` had been built 2026-08-05 17:28 and was never
  rebuilt. For twenty days the panel published **$40,279,500 / 557 filings** on
  `TRBF-SRPMCP-00`, making an Arizona public power and irrigation district the
  **#2 Native lobbying entity in America**. Now **$10,414,000 / 141**.
- **FA-01b.** The org-type guard is a NAME-FORM bar. It caught `MINES` and
  missed `MINING`; it caught `CITY OF SANTA ROSA` and left `SANTA ROSA COUNTY
  FL`, `SANTA ROSA JUNIOR COLLEGE`, two hospital systems and a Florida economic
  development council attributed to a California tribe. **471 filings /
  $5,756,834**, withdrawn. `TRBF-SROSAR-00` now holds its own 13 filings /
  $210,000 and nothing else.
- **FA-02.** 94 `foia_request_index.csv` rows keyed to the Native Village of
  Georgetown, Alaska because `georgetown.edu` sat in a list of email domains a
  requester asked the agency to search. A prior pass DEMOTED and FLAGGED them.
  **A demoted wrong link is still a wrong link in a shipping column.** 109 rows
  unlinked (94 Georgetown + 15 of 17 Enterprise); linked rows 453 → 344.

### How it is enforced now, and the two things that make it not an excuse

`code/354_correction_register.py` + `data/clean/cedar_correction_register.csv`.
Every APPLIED correction is DECLARED as an **(entity_id, subject)** pair that
must no longer co-occur in any row of any table in `data/clean`.
`62_no_regression_check.py` imports it — never a second copy of the registry —
and carries **`corrections_not_propagated`**.

1. **The subject, never the match phrase.** The phrase was tried first and it
   fails in both directions: `TRBF-ENTPRS-00`'s phrase is the bare word
   `Enterprise`, two rows carrying it are CORRECT, and testing on the phrase
   flagged 306 `prime_contracts` rows whose recipient name merely contains the
   English word. The subject of a lobbying attribution is the **client name**;
   the subject of a FOIA link is the **request id**. Both are what a sibling
   table would carry if it re-derived the same wrong link.
2. **Cells in a `*withdrawn*` column are excluded.** Otherwise a correction
   recorded honestly — `attribution_withdrawn_entity_id`,
   `tribe_entity_id_withdrawn` — reports itself as its own unfixed consumer,
   and the only way to a clean check would be to erase the evidence.

**THE SHIPPING ALLOWANCE.** `ship_dist_rows` is MUST_NOT_FALL on the stated
grounds that *"there is no benign cause"*. Withdrawing 54 false panel rows is a
benign cause and was not anticipated. Per `62`'s own rule 2 — show it is not a
defect, change the check, say why — a fall is now allowed **only when the
register declares a `rows_removed` total EXACTLY EQUAL to the fall**. Exact,
never `<=`: one more lost row and the arithmetic stops matching and the line
fails again. That is the difference between an allowance and an acknowledgement
button. It printed, on the first run after the fix:

    ** tribe_year_lobbying_panel.csv shipped 5,051 -> 4,997, EXACTLY the 54
       row(s) the correction register declares withdrawn as false
       attributions. Allowed and named.

**And the stale consumers are PRINTED BY NAME every run**, with the column and
an example row — defect class 2c applied to the gate's own output.

### THE BIGGEST THING THIS FOUND, AND IT IS NOT FIXED — `FA-04`

The propagation check found it on its first run: **`BRISTOL BAY AREA HEALTH
CORPORATION` is attributed to `ANRC-BRBYCO-00`, Bristol Bay NATIVE
CORPORATION**, in ten places. Root: **one tier-B `cluster_v3` row** on UEI
`NL5HNWNUFMK4` in `cedar_identifier_ledger_final.csv`, `tier_rationale =
"Algorithmic name clustering, unreviewed"`. BBAHC is a tribal HEALTH
organisation (EIN 920044965, Dillingham AK); BBNC is the ANCSA regional
corporation. There is no BBAHC entity in the spine, which is why the clusterer
reached for the nearest name.

**`federal_funding_transactions.csv`: 504 rows, $494,305,407 obligated.**
Plus `cedar_identifier_graph_nodes` (UEI node: 676 rows / $776.7M observed),
`subawards` 29, four FAC Single Audits, `np_schedule_i_grants` 4,
`native_passthrough` 4, and the tiered ledger and propagation rows.
**And a second, unaudited instance beside it: 50 more assistance rows key
`BRISTOL BAY HOUSING AUTHORITY` to the same id — so every assistance row
attributed to BBNC is attributed to an organisation that is not BBNC.**

**Deliberately not fixed here.** Unlinking it moves
`village_corp_obligations_usd`, MUST_NOT_FALL at $60.4B, and the right answer is
a **REPOINT** — BBAHC and BBHA are real Native organisations that should be
spine entities — which is an owner's ruling, not a drive-by edit at the end of a
session. Written up as **FA-04** in `docs/ANOMALY_REPORT.md`, wired as a
standing regression in `227_anomaly_sweep.py`, and it is the entire floor of
`corrections_not_propagated = 10`.

### The consumer that could have re-imported the whole correction

`180_build_lobbying_registrant_hub.py` and
`182_rule_lobbying_registrant_native_ownership.py` filtered on
`org_type_barred` alone, because on 2026-08-06 that was the only withdrawal mark
there was. A second mark, written correctly, would have been invisible to them
and all 471 filings would have come back on the next run.

> **This project's signature failure, with the arrow reversed: not a correction
> that failed to reach a consumer, but a CONSUMER THAT CANNOT SEE A CORRECTION
> because it tests for one specific spelling of it.**

One predicate, declared once: **`cedar_domain.lobbying_attribution_withdrawn`**,
which reads every mark and every withdrawal sentinel. Add the next mark THERE,
never at a call site. `n_filings_org_type_barred` deliberately keeps its
documented meaning (script-65 only) — widening a column's contents while keeping
its name is how `extent_competed` became two vocabularies.

### STILL STALE, NAMED NOT FIXED

`lobbying_registrants.csv` (653 rows) and
`lobbying_registrant_concentration.csv` (36) carry per-registrant and
concentration AGGREGATES computed over the 471 withdrawn filings. **They carry
no (entity, client) pair, so the propagation check cannot see them — an
AGGREGATE consumer carries the defect without carrying the evidence of it, and
that is a real limit of a pair-based check, stated rather than papered over.**
Fix: run `180` then `182`, in that order, on a quiet machine. Expect
`lobbying_registrant_client_relationships.csv` to drop ~18 rows on that run:
`180` deletes a withdrawn pair outright, where `353` unlinked it in place and
kept the row (the firm really did represent Santa Rosa County FL; only the
tribal claim was false). **Declare that drop in the correction register first or
`62` will fail on it.**

### What was written, and what would revert it

| file | by | reverted by |
|---|---|---|
| `native_entity_lobbying_disclosures.csv` | 350 | `code/lobbying_pull/05_match_filings_v2.py` — a FULL rebuild from `raw_filings.jsonl` that reverts **65 and 350 both**. If 05 is ever re-run: 65, then 350, then 351, then 353, **then 1091**. |
| `native_entity_lobbying_disclosures.csv` — the four `supersession_*` / `is_superseded` columns | **1091** (2026-09-02) | the same 05 rebuild, and anything else that rewrites the 40-column file. `1091` is **idempotent and recomputes rather than appends**, so the recovery is just `py -3 code/1091_lobby_amendment_supersession.py apply`; it refuses to overwrite an existing dated backup. `287`/`build.py plan lobbying` now list it in PHASE 2. **It had to be made visible to them:** the first draft wrote through a `path=TARGET` parameter, so no line naming `TARGET` carried a write verb and `cedar_pipeline.declared_io` filed 1091 under `readers/` for a file it rewrites — the same shape as the `845` finding. |
| `tribe_year_lobbying_panel.csv` | 351 | the same 05 rebuild |
| `foia_request_index.csv` | 352 | `136_build_congressional_correspondence_and_foia_index.py`. After any 136 rebuild: 168, then 352 — the enricher runs LAST. |
| `lobbying_issue_families_filing.csv`, `lobbying_registrant_client_relationships.csv` | 353 | 180/182 (now patched so they cannot re-import) |
| `dist/cedar_press.db` (5 tables + the register) | 355 | **`25_build_publication_layer.py` REPRODUCES this fix, it does not revert it** — the clean files are correct, so a rebuild propagates it. The one rebuild/in-place collision in this repo that runs the right way. |
| `docs/ANOMALY_REPORT.md` FA section | hand | **`227_anomaly_sweep.py` REGENERATES that whole section.** Its FA-01/FA-02 generators and note text were rewritten and FA-04 added, so a re-run reproduces the corrected substance instead of reverting it. **FA-02's detector was itself broken and is fixed:** it scanned for `georgetown.edu` in four columns the string never appears in, and scored 94 by accident on the `georgt` substring of the entity id — so it would have read clean the moment the id was blanked, even if the bad link returned through another column. **A regression detector that cannot see the defect it re-tests is worse than none.** It now measures the LINK. |

**Never re-tiered to X, anywhere.** X blocks the whole identifier downstream in
`169_build_identifier_graph.py`; blacklisting `TRBF-ENTPRS-00` would have
suppressed the two FOIA rows that genuinely are Enterprise Rancheria, and
blacklisting `TRBF-SROSAR-00` its 13 real filings. **The identifiers are sound.
The LINKS were not. Unlink the link.** Every withdrawal keeps its
`matched_alias` / `tribe_match_phrase` provenance and adds a `*_withdrawn_*`
block carrying the id that was removed, the verbatim evidence and the reason — a
correction has to be VISIBLE and reversible, not erased. The prior DISPUTED
audit text is carried forward verbatim inside the new audit string.

### Two things that were deliberately NOT swept

- **55 FOIA rows remain `DISPUTED_FREE_TEXT_SINGLE_TOKEN` at tier B** —
  Shinnecock 7, Metlakatla 7, Ewiiaapaayp 7, Chickaloon 6, Muckleshoot 5,
  Seminole Tribe of Florida 5, Narragansett 5, and ten more. Unlike
  `georgetown` and `Enterprise`, these are distinctive tribal names appearing in
  prose *about those tribes*, and a request about the Shinnecock is plausibly a
  `SUBJECT_OF_REQUEST` link. **An unlink needs evidence exactly as much as a
  link does.** They need reading one at a time, not a rule.
- **Two Enterprise FOIA rows were KEPT**, one CONFIRMED (the text names
  "Enterprise Rancheria of Maidu Indians of California") and one RETAINED at
  tier B with the doubt named: an AS-IA land-to-trust decision-letter request
  whose parsed description truncates at *"...by the Enterprise"*.

### Baseline note, stated so it is not mistaken for re-baselining

`data/clean/_regression_baseline.json` gained **two metrics that never had a
floor**: `corrections_declared` = 163 and `corrections_not_propagated` = 10.
**No existing metric was touched**, and the ten are FA-04, named above and
printed by the gate on every run. Backup:
`_regression_baseline.json.bak_2026-08-26_pre_354_correction_register`.

---

## NAMED GATE FAILURE — three owners, none of them the taxonomy pass (2026-08-26 ~20:50)

Per standing rule 15 option 3. `62_no_regression_check.py` was **RED BEFORE this
pass began and RED after**, and **the failing set is not the same set** — it
changed twice while the work ran, because three other agents were live in the
repo at the time. Recording which is which, so the next reader does not inherit
an unowned failure.

Owner of this note: **`code/374_build_cedar_taxonomy_export.py`**, the taxonomy
consolidation (`docs/CEDAR_TAXONOMY.md` + `docs/CEDAR_TAXONOMY.json`). It writes
**one file, in `docs/`**, reads everything else, and **moved no gate metric in
either direction.** `293_lint_bug_classes.py` reports **zero findings against it**
and `TOTAL (unwaived)` was **151 before and 151 after** its own runs.

### FAILURE 1 — `lint_class2c` 60 → 62, `lint_new_defect_instances` = 2

    class2c 382_remine_property_site_corpus.py:      stats["capacity_refused_implausible"] += 1
    class2c 384_crawl_uncrawled_open_properties.py:  stats["hosts_stopped_on_first_refusal"] += 1

**OWNER: the property-site crawling agent** — `code/382_remine_property_site_corpus.py`
(written 20:40), `code/383_adjudicate_property_site_refusals.py` (20:45),
`code/384_crawl_uncrawled_open_properties.py` (20:47). **This is live work, not
abandoned work; editing it would race its author.**

**WHAT HAS TO HAPPEN.** Class 2c is *a drop counter that does not NAME what it
dropped*. `87` counted `"skipped: not a documented dataset"` and never printed
the filename — **33,817 rows invisible for twenty days**. Both counters here are
refusals, which is exactly the case where the name is the whole value: a count of
"N capacities refused as implausible" is not actionable and scrolls past, while
*"refused WinStar at 9,999,999 devices"* is a task. Add the identifier to the
counter, or waive the line with a reason. **Do not `--baseline` it away.**

Earlier in the same evening this metric sat on
`353_propagate_lobbying_corrections_to_consumers.py`, which has since cleared.
The count is stable at +1/+2 over a moving population, so **the floor is holding
and the instances are churning** — which is the gate working.

### FAILURE 1b — two more owners appeared while this note was being written

Re-measured at the close of the pass. `lint_new_defect_instances` is **4**, not
2, and the extra two are also not the taxonomy pass:

    class6  98_build_oira_and_hearings.py : hearing_appearances.csv
    class7  293_lint_bug_classes.py       : its own two waived `id()` lines

**OWNER of the class6: the agent on `98_build_oira_and_hearings.py`.** It carries
`# lint-ok: class6 - THE ORDERING IS WRITTEN DOWN, HERE, BY A PERSON`, which is
the correct disposition for a rebuild/enricher pair whose ordering a static
analyser cannot infer. It reads as new because the file moved, not because the
reasoning changed.

**OWNER of the class7: whoever is editing `293_lint_bug_classes.py` right now.**
Its two `id()` waivers shifted line 512 → 536 and 244 → 268 between two runs
twenty minutes apart, so **the linter's own waiver lines moved and its own
findings re-registered as new.** They are Python object identity on an in-memory
AST node inside one process, never written to a file — the disposition is
unchanged and correct.

**And one metric moved in both directions inside this pass.** `lint_class1` read
`ROSE 0 -> 1` on one run and `CLASS1 0` on the next, with no class1 finding named
in either. **That is measurement churn from a file being edited mid-scan, not a
defect** — and it is worth writing down that on a repo with ten live agents, a
single gate run is a sample, not a state. Run it twice before you name an owner.

### FAILURE 2 — `FA-01`, ten rows across nine tables, a NEW check

    federal_funding_transactions.csv   504 rows still key ANRC-BRBYCO-00 to 'BRISTOL BAY AREA HEALTH CORPORATION'
    subawards.csv                       29 · native_passthrough.csv 4 · np_schedule_i_grants.csv 3+1
    cedar_identifier_graph_nodes.csv     2 · cedar_identifier_ledger_final.csv 1
    cedar_identifier_ledger_tiered.csv   1 · cedar_identifier_propagation.csv 1
    fac_tribal_single_audits.csv         1

**OWNER: the lobbying-correction / correction-register agent** —
`65_lobbying_organization_type_guard.py`, `350_withdraw_false_lobbying_attributions.py`,
`353_propagate_lobbying_corrections_to_consumers.py`, `354_correction_register.py`.
The `FA-01` check is that agent's own, added to `62` at line 851, and it is
**doing its job**: `350` withdrew the Bristol Bay Area Health Corporation
attribution in the lobbying layer, and this check finds the same false key still
live in nine consumers.

**This failure did not exist in the 20:0x run and appeared by 20:50** — the check
landed between the two. **That is a new detector finding a real pre-existing
defect, not a regression**, and it is the best possible reason for a gate to go
red. It is exactly this project's signature failure shape: *a correction made in
one place that never reached its consumers.*

**WHAT HAS TO HAPPEN.** Run the propagation the register already knows about —
`353_propagate_lobbying_corrections_to_consumers.py` — against the nine tables
named. Note `cedar_identifier_ledger_final.csv` is on the list, so **back it up
first and re-run `62` after**, per the standing sequence.

### WHAT CLEARED between the two runs, recorded so nobody re-fixes it

`ship_tables_at_zero` 139 → 138 · `tables_missing_codebook_block` 140 → 139 ·
`tables_missing_from_25_TABLES` 235 → 234 · `tables_missing_from_27_SPEC`
250 → 249 · `tables_missing_notes_contract` 140 → 139, and the
`tribe_year_lobbying_panel.csv` un-shipping (5,051 → 4,997). All five registry
metrics were the single unregistered `cedar_correction_register.csv`, and its
owner registered it. **Nothing needs doing here.**

### The standing point this run adds

**A gate that is red for one reason at 20:00 and red for a different reason at
20:50 is a WORKING gate, and reading only the pass/fail bit loses that.** The
"pre-existing, not mine" trap that cost six sessions is not avoided by comparing
exit codes; it is avoided by **diffing the failing LINES**. Both runs of this
pass are on disk for exactly that comparison, and the diff is what showed that
five failures cleared and one new detector fired — neither of which a `FAIL` told
anyone.

---

## THE TAXONOMY IS CONSOLIDATED — `docs/CEDAR_TAXONOMY.md` (2026-08-26)

The owner asked for *"a taxonomy of our own with more data."* **One already
existed and nothing held it.** It is now in two files:

    docs/CEDAR_TAXONOMY.md      the human artefact - a subscriber and a future agent both read this
    docs/CEDAR_TAXONOMY.json    15 layers, machine-readable, what the product renders behind `method`

    py -3 code/374_build_cedar_taxonomy_export.py --check   # would it change? no write
    py -3 code/374_build_cedar_taxonomy_export.py

**It IMPORTS rather than transcribes.** Every vocabulary that lives in a module is
read from that module and every count is recomputed from `data/` at build time.
Only the definitions are prose, because a definition is the one thing a file
cannot compute about itself. **Regenerate it after any change to
`cedar_domain.py`, the spine, or the certification layer.**

**Four things in it that change what a reader should do:**

1. **`Federally recognized tribe` is NOT the federally recognized universe.** 349,
   plus 228 `Federally recognized Alaska Native Village`, is 577. The split is
   geographic. Quoting 349 understates it by 40%.
2. **`reported_native_preference` is the union INCLUDING 8(a) and 98.8% of its
   dollars ARE 8(a)**, a programme with no Native content. Genuinely
   Native-specific set-asides are **$1.2005B, 0.4905% of $244.77B attributed**.
   The union is exact and is verified at build time.
3. **THE PREFIX DOES NOT IDENTIFY THE CLASS.** `ANVC` spans village AND group
   corporations; `CDFI` spans Native CDFIs AND Native Financial Institutions.
   `41_build_codebooks.py:1338-1340` says *"Join to the spine on this prefix"* and
   that instruction is wrong for 272 entities.
4. **The comparative certification taxonomy is DESCRIPTIVE, never PRESCRIPTIVE.**
   We publish *"Colville's Title 10 certification does not require an ownership
   percentage"*. We never publish *"therefore this firm is not really
   Native-owned."* `374::FORBIDDEN_TAXONOMY_KEYS` refuses to write any layer
   carrying a field that adjudicates, and `main()` aborts on one.

**Eight gaps are NAMED in it and re-measured on every run** — including two that
are worth a separate pass:

- **`ANCSA_CLASS_GUARD_UNCALLED`.** `bears_ownership()` fires ANCSA RULE 2 and
  RULE 4 only when the class arguments are passed, and **no production caller
  passes them.** `ANCSA_CORPORATION_CLASSES` and
  `ALASKA_VILLAGE_GOVERNMENT_CLASSES` have **zero importers.** The $24.52B ruling
  WAS applied — by `191` using its own local copy of the class sets. **The ruling
  was enforced and the reusable guard was not.**
- **`CODE_USES_A_CLASS_STRING_THE_SPINE_DOES_NOT_HAVE`.** `103_build_california_gaming.py`
  and `105_build_florida_gaming.py` refuse `"Native CDFI"` and
  `"Native financial institution"` — **neither string is in the spine**, so 93
  entities are not refused; `107_pull_remaining_states.py` uses the long forms and
  gets it right. `cedar_match_guard.py`'s `MUST_REFUSE` fixture asserts on the
  same dead string, so **it passes vacuously.** The near-miss scan in
  `374::scan_code_for_entity_class_literals` is proposed as a new class for `293`;
  nothing detects this shape today.

**Related, and it is the reason the whole thing was worth doing:** the
entity-class vocabulary is re-typed in **42 build scripts**, under three variable
names per concept, **with member sets that genuinely disagree** — and
`cedar_domain.py` declares none of them, so there is nowhere the disagreements
could be reconciled or even seen side by side.

---

## A CORPORATE FAMILY STEM IS NOT A FIRM IDENTITY (2026-08-26, script 324)

`NAME_TRAPS` blocks a token that is a PLACE or a NATION. This is the same defect
one level up: **a token shared by a whole CORPORATE FAMILY cannot distinguish
within it.**

Matching the certified firm *"ASRC Federal NetCentric Technology"* against
`subawards.csv` returned **eighteen distinct ASRC Federal subsidiaries** on the
overlap `{asrc, federal}`. Two non-generic, non-trap tokens cleared every guard
we had — and the match was still wrong. It identifies the **family** correctly
and the **firm** not at all, and being right about the parent is exactly what the
parent's own directory already told us. Eighteen review cards that all say "an
ASRC company" cost a reviewer's attention and add nothing.

> **THE RULE: if one asserted firm matches THREE OR MORE distinct
> counterparties on the SAME overlap token set, that set is a STEM, not an
> IDENTITY. Refuse the whole group, and NAME what was refused.**

`324` implements it (`FAMILY_STEM_THRESHOLD = 3`, `demote_family_stems()`), and
it took subaward name-candidates from 36 to 2 — the two survivors being exact
name variants of Doyon Project Services. **34 refusals, each printed by name**,
per the standing rule that a drop counter which does not name what it dropped is
invisible.

Worked example of the older trap, from the same run: the stem `nana` matched
**`PANANA DELENA` (OK)**, which is not NANA.

---

## `SITE_UNREACHABLE` IS NOT A NEGATIVE, AND IT MUST NOT ENTER A DENOMINATOR (2026-08-26)

Four of 62 tribal hosts refused this client on every path: Turtle Mountain and
San Carlos Apache (HTTP 403 / 307 on all HTML), Kotzebue (403 including
`/robots.txt`), White Mountain Apache (expired TLS). **The hosts exist and
answer.**

`318_measure_tribal_vendor_list_payoff.py` excludes them from the publication
rate. Counting them as `NO_LIST_FOUND` would publish **our own access problem as
a fact about the source** — defect class 2, the most expensive class, because
the output looks like a finding.

**San Carlos is the case that proves it.** Its `robots.txt` and every sitemap
serve HTTP 200, and `page-sitemap.xml` shows **two distinct TERO pages** —
`/tribal-employment-rights-office/` AND `/tero-2/`. Only the HTML is filtered.
Recording that as "no TERO list" would have been false in a way nothing
downstream could catch.

**Related: an unreadable TERM is not an absent term.** Where a WAF blocked
`/robots.txt` itself, `source_terms_status` is `NOT_CHECKED`, never `SILENT`.

**And two things that look like blocks and are not:** `ohkay.org` serves an
expired certificate and `maliseets.com` a certificate valid only for
`*.townsquareinteractive.com`. Both were reached with a cert-ignoring client and
both are genuine negatives. `redlakenation.org`'s apex serves an IIS7 default
page while the live site is on `www.` — **query the wrong host and you
manufacture a false unreachable.**

---

## THREE HIJACKED DOMAINS IMPERSONATING TRIBES — BLACKLIST (2026-08-26)

Found while sweeping 62 tribal hosts. All three are plausible-looking official
URLs that now serve unrelated commercial content. **None may enter a host list,
a source URL, or a citation.**

| domain | now serves | the real host |
|---|---|---|
| `oglalalakotanation.net` | an **offshore online casino impersonating the Oglala Sioux Tribe**, via a Cloudflare Workers subdomain | `oglala.gov` |
| `cheyenneriversiouxtribe.org` | 301 → `laurenscounty.us` | `cheyenneriversioux.com` |
| `whitemountainapache.org` | 301 → `sticksushi.es` | `wmat.us` |

Also: much "Akwesasne business directory" material online belongs to the
**Mohawk Council of Akwesasne (Canada)**, a different government from the Saint
Regis Mohawk Tribe. Do not conflate.

---

## A CERTIFICATION IS NOT SELF-DESCRIBING — PUBLISH THE RULE BESIDE IT (2026-08-26, script 323)

`data/staging/tribal_vendor_lists/tribal_certification_rules_2026-08-26.csv`,
built by `code/323`. One row per (tribe, programme), with the eligibility rule
**quoted verbatim** with a URL and a capture date. The build **refuses** to
write `RULE_FOUND` or `RULE_PARTIAL` without both a quote and a source URL, and
refuses `RULE_NOT_PUBLISHED` without a `searched` value.

> **A RULE IS QUOTED, NEVER INFERRED FROM THE CONTENTS OF THE LIST.** Deriving
> "they must require 51%" from a spreadsheet is our claim wearing the tribe's
> authority — defect class 2 in its purest form.

**Why the table exists, measured across 14 programmes:**

- **Ownership floors are 51%, 60% or 100%.** Colville and CTUIR are **60**; MHA
  is **100**. **A blanket 51% filter silently mis-states three programmes.**
- **10 of 14 require a percentage at all; 1 requires none; 3 do not state one.**
- **Colville is a genuine CONTRADICTION, not a definitional difference.** Its
  published list flags firms `Certified Title 10 = Yes` at 0% Indian ownership,
  while Colville Tribal Code §10-3-4(h) reads: *"No contractor or subcontractor
  shall qualify for preference if Indian ownership in, or control of, the
  business is less than the required minimum percent at any time..."* Publish
  the rule beside the flag and let the contradiction show. Do not drop the rows;
  do not infer a threshold.
- **Two lists misdescribe their own rule.** EBCI's says "TRIBAL MEMBER owned"
  when its Priority 2 admits any federally recognised tribe at 51%. CSKT's
  legend describes a *person's enrolment* where the ordinance tests *firm*
  ownership plus management control.
- **MOST OF THESE CERTIFICATIONS ARE NOT EVIDENCE OF CITIZENSHIP IN THE
  CERTIFYING NATION.** Oneida §502.3-1(t) says it outright: *"'Indian
  preference' means preference for Indians, regardless of tribal affiliation."*
- **The weakest assertion says so itself.** Calista's Calivika: *"Calista does
  not investigate or evaluate the listed businesses in any way."* Eligibility is
  "at least one qualified individual" — satisfiable by a **1% owner**, and
  **spouses and grandchildren qualify**, so a listed business may have no Native
  owner at all.

`whose_ownership` separates populations that DO NOT NEST and must never be
collapsed: `THIS_TRIBE_MEMBER` / `ANY_FEDERALLY_RECOGNIZED_TRIBE_MEMBER` /
`ANY_NATIVE_PERSON` / `TRIBAL_GOVERNMENT_ENTITY` /
`SHAREHOLDER_OR_DESCENDANT_OR_SPOUSE` / `PARENT_CORPORATION`.

---

## "TERO" IS THE WRONG SEARCH TERM — NINE CONFIRMATIONS (2026-08-26)

Recorded once at 13 lists; it now has nine separate-domain confirmations across
62 entities and should be treated as **the primary discovery step, not a
fallback**:

`cherokeetero.com` · `ebci-tero.com` · `mhatero.com` · `tulaliptero.com` ·
`btero.com` · `wstero.com` · `chickasawbusinessnetwork.com` ·
`shop.fcpotawatomi.com` · `fortpecktero.org`

**Blackfeet is the extreme case.** The word "TERO" appears NOWHERE in
`blackfeetnation.com`'s sitemap; neither its Economic Development nor its
Employment page mentions it. The only pointer to `btero.com` was a **plain-text
phone-book entry in the Tribal Directory staff listing**, reachable only through
the WordPress `?s=` search.

Two companions:

- **Sitemap enumeration beats navigation.** **Lummi's own Business Directory
  page renders "no documents currently available" while the identical report is
  live at two other paths** — navigating by the site's own directory manufactures
  a false negative.
- **Pueblo of Laguna files its TERO under TAX ADMINISTRATION.** No employment-
  or business-oriented navigation reaches it. Department-agnostic sitemap
  keyword grep is now a standard step.

**And "vendor" is a false friend in both directions.** Muscogee's file is titled
*"MCN CESO Vendor List"* and is a certified 51%-Indian-owned roster; Poarch's
on-site search for "vendor" returns **pow-wow craft vendors**; Saint Regis
Mohawk's `robots.txt` disallows `/vendor/`, a **Composer directory**. Only the
governing ordinance settles it — always pull the code.

---

## A THIRD PROVENANCE RESTRICTION IS MACHINERY, NOT PROSE (2026-08-26, script 321)

`cedar_codebook.TRIBAL_SOURCE_RESTRICTED_FILES` sits beside
`LICENSED_SOURCE_FILES` (Casino City) and the D&B pre-2022-04-04 rule.
`code/321_gate_tribal_source_restriction.py` fails a build on five checks and
carries a **seven-case `--selftest`**, because a detector narrowed until it stops
seeing its own defect reports clean.

**A federal record is public by statute. A sovereign government's own
publication is not the same thing, and "publicly reachable" is not "licensed for
commercial redistribution." SILENCE IS UNRESOLVED, NEVER PERMISSION.**

Removal is one field — and so is admission, because some TERO offices will want
the reach and **saying yes must be as cheap as saying no**. All 62 authorities
are `UNRESOLVED` and every staged row is `publishable = N`.

**Two robots stops honoured, and both close the archive route too:**
`elyshoshonetribe.com` and `penobscotnation.org` both name `ClaudeBot` under
`Disallow: /`. Both are `wayback_priority = EXCLUDED`. On Penobscot, a handful of
pages had been fetched before `robots.txt` was read; **collection stopped on
discovery and the disclosure is recorded on the row rather than tidied away.**

**Lummi's `robots.txt` disallows `/apps`** — the exact path the tribe's own page
uses to link its business directory. That path was not fetched; the identical
report at `/widgets/` is permitted and that is the copy taken. Any re-run must
use `/widgets/`.

---

## NAMED GATE FAILURE — three lint classes, three owners (2026-08-26 ~20:53)

Recorded under standing rule 15 option 3 / concurrency rule 3, **before** the
canonical-identity-layer pass (`docs/CEDAR_ID_SYSTEM.md`, `code/cedar_ids.py`,
`code/415`–`code/419`) wrote anything. `62_no_regression_check.py` and
`293_lint_bug_classes.py` were both run first, and **not one failing line is
this pass's**.

| failing metric | movement | the instance | owner, by mtime |
|---|---|---|---|
| `lint_class1` | 0 → **1** | `399_inventory_stranded_data.py`: `for p in sorted((INTERIM / "ocr_shards").glob("*.csv")):` | written **20:50** — the stranded-data inventory agent |
| `lint_class2c` | 60 → **62** | `382_remine_property_site_corpus.py`: `stats["capacity_refused_implausible"] += 1` · `384_crawl_uncrawled_open_properties.py`: `stats["hosts_stopped_on_first_refusal"] += 1` | **20:40** and **20:52** — the gaming property-site re-mine agent (`382`–`386`) |
| `lint_class6` | — | `98_build_oira_and_hearings.py` vs `hearing_appearances.csv` | **18:32** |
| `lint_new_defect_instances` | 0 → **3** (4 on the next run) | the sum of the above | |

All four files were written **between 13 minutes and 1 minute before the gate
ran**, against a 293 baseline recorded earlier the same evening. **This is
in-flight work, not abandoned work**, and editing another agent's live script is
the collision concurrency rule 5 exists to prevent.

**WHAT HAS TO HAPPEN.**
- `399`: a `glob()` over a parts directory is class 1 only if `399` is a
  CONSUMER. If reading the shards IS its job it needs a one-line waiver
  (`# lint-ok: class1 - 399 inventories the parts; that is the whole job`), or
  a `PROMOTED_TABLES` entry naming the promoted table those shards belong to.
- `382` / `384`: **name what the counter dropped, in the same block.** A count
  scrolls past; a filename is a task. Or waive with a reason.
- `98`: declare the ordering between the full-rebuild writer and the in-place
  enricher on `hearing_appearances.csv`, enricher last.
- Then `py -3 code/293_lint_bug_classes.py --baseline` by that owner —
  **not by anyone else**, because a floor re-recorded by a bystander swallows
  the bystander's own findings too.

**Also still failing and already named three times in this file:** the `FA-01`
correction-propagation lines (`BRISTOL BAY AREA HEALTH CORPORATION` still keyed
to `ANRC-BRBYCO-00` in 8 tables) belong to the lobbying/FOIA correction pass
(`350`–`358`). Not re-litigated here.

**What this pass did instead of stepping around it:** named it here first;
wrote **no new table to `data/clean/` without a codebook fragment**; touched
`data/spine/cedar_entity_spine.csv` and `data/clean/entity_aliases.csv`
**additively and in place only**, columns added and never removed, backups
tagged with the full script name, `.part`-then-rename, and every output re-read
from disk after writing. `293` was re-run after and reported **no class rose on
this pass's account**.


---

## NAMED GATE FAILURE — Bristol Bay ruling FA-01 + two live crawlers (2026-08-26 ~21:1x)

Per standing rule 15 option 3, named before continuing. `62` FAILS on two
independent groups, **neither of which is the tribal certification build
(`316`-`324`)**.

**GROUP 1 - `lint_new_defect_instances = 4`. OWNER: two LIVE crawlers.**

| class | script | live now? |
|---|---|---|
| class2c | `382_remine_property_site_corpus.py` - `stats["capacity_refused_implausible"] += 1` | **YES, running** |
| class2c | `384_crawl_uncrawled_open_properties.py` - `stats["hosts_stopped_on_first_refusal"] += 1` | **YES, running** |
| class6 | `98_build_oira_and_hearings.py` - `hearing_appearances.csv` | - |

Both class2c instances are the same shape and both are ironic given what they
count: **a refusal counter that does not NAME what it refused is exactly the
defect**. `hosts_stopped_on_first_refusal` should print the hostnames; a count
of hosts that refused us is not actionable and scrolls past. **WHAT HAS TO
HAPPEN:** name the dropped units, or waive with a reason
(`# lint-ok: class2c - why`). For the class6, establish the ordering on
`hearing_appearances.csv` and make the enricher run LAST.

**GROUP 2 - ruling FA-01 not applied back.** `ANRC-BRBYCO-00` is still keyed to
`BRISTOL BAY AREA HEALTH CORPORATION` across **9 tables and ~547 rows** -
`federal_funding_transactions` 504, `subawards` 29, `native_passthrough` 4,
`np_schedule_i_grants` 3+1, `cedar_identifier_graph_nodes` 2, and one row each
in `cedar_identifier_ledger_final`, `cedar_identifier_ledger_tiered`,
`cedar_identifier_propagation` and `fac_tribal_single_audits`.

**OWNER: whoever recorded FA-01.** This is the standing rule arriving again:
**a ruling that is not applied back to its source table is not a ruling, it is
a note.** Apply with the `124_apply_rulings_in_place.py` pattern - never `09`
or `01`. Note the ruling has to reach BOTH ledger vintages and the propagation
table, or it will resurface.

**NOT THE TRIBAL CERTIFICATION BUILD.** All nine scripts `316`-`324` lint clean
against every class (verified by grepping `293`'s own output for their
filenames: zero hits), and they write ONLY to `review/`, `docs/`,
`docs/codebooks/` and `data/staging/tribal_vendor_lists/` - nothing to
`data/clean/` or `dist/`, which `321` enforces as a gate rather than a promise.
`321_gate_tribal_source_restriction.py` PASSES, and its `--selftest` passes all
seven fixtures.

### ADDENDUM, same note, ~20:55 — three MORE named gate failures, all owned elsewhere

`62_no_regression_check.py` re-run at the close of the CourtListener pass:

| failing metric | movement | owner |
|---|---|---|
| `lint_class2c` | 60 → 62 | `code/382_remine_property_site_corpus.py:` `stats["capacity_refused_implausible"] += 1` and `code/384_crawl_uncrawled_open_properties.py:` `stats["hosts_stopped_on_first_refusal"] += 1` |
| `lint_class6` | 33 → 34 | `code/98_build_oira_and_hearings.py` on `hearing_appearances.csv` |
| `lint_new_defect_instances` | 0 → 4 (3 still standing) | the three above |

`382` and `384` carry mtimes of 20:40 and later on 2026-08-26 — they landed
*during* this pass. Class 2c is the counter-that-does-not-name-what-it-dropped:
both are refusal counters in a crawler, so the fix is one string each — print
the host or the property that was refused. A count is not actionable; a name is
a task.

**`py -3 code/293_lint_bug_classes.py` names zero findings in `code/366`
through `code/372`, checked explicitly.** And two metrics moved the strict way
in the same run: `lint_class7` **74 → 42** and `lint_bug_class_instances`
**182 → 154**, so class 7 is well under the 73 that must not rise.


---

## THE 139 UNSHIPPED TABLES WERE NOT ALL A BACKLOG (2026-08-26 ~21:00, scripts 391-392)

`docs/SHIP_GAP_REPORT.json` counted **139 tables at a 0% ship ratio**, 731,181
rows, and printed the same one-line fix against nearly all of them: *"register
a codebook block, then re-run the full 7-step ship chain (`py -3 code/build.py ship`; “87 → 25 → 27” is a 3-step shorthand that omits the codebook build, the gate, the coverage profile and the harmonised views)."*

That line is right about the MECHANISM and wrong about the DECISION. Doing it
to all 139 would have published harvest scratch, hand-coded audit sheets,
review queues with a `YOUR_RULING` column still empty, and 20 measurements of
our own collection. Triaged one table at a time in
`code/391_triage_unshipped_tables.py`:

| verdict | tables | rows |
|---|---:|---:|
| **SHIP** | 80 of the 139 (+4 collision siblings) | 487,251 |
| **INTERNAL, deliberately** | 56 | 109,097 |
| **NEEDS A RULING** | 3 | 2,441 |
| **NEVER SHIP** (vendor-licensed) | 2 | 132,392 |
| EMPTY (0 rows) | 1 | 0 |

**THE RULE THIS EARNS: A GAP COUNTER THAT CANNOT TELL "NOBODY GOT ROUND TO IT"
FROM "WE DECIDED NOT TO" REPORTS A BACKLOG THAT CAN NEVER REACH ZERO — and a
backlog that can never reach zero stops being read, exactly like a gate that is
always red.** So a deliberate non-ship is now a DECLARATION, not an absence:
**`cedar_codebook.INTERNAL_TABLES`**, 56 entries each with its reason, sitting
beside `LICENSED_SOURCE_FILES` and `TRIBAL_SOURCE_RESTRICTED_FILES`.
`registered_tables()` returns those files in neither the shippable nor the
undocumented list, and `87` NAMES them on stdout under `INTERNAL BY DECISION`,
because "we refused it" and "we never noticed it" must not look the same in the
output. It is NOT the licence gate and must not be confused with it: a licensed
file may never ship on somebody else's terms; an internal one is ours and the
decision is reversible by deleting a line.

**A SUBSET HEADER IS A BACK DOOR ONTO THE SHELF.** `87` assigns a file to its
best-OVERLAPPING block, so a table needs no block of its own to ship — it only
needs its columns to be a subset of a sibling's. `cedar_identifier_ledger_
tiered.csv` has a header IDENTICAL to `cedar_identifier_ledger_final.csv`, and
`cedar_spiderweb_v2.csv` is a 0.60 subset of `cedar_publishable_identifiers.
csv`. Both would have shipped off the back of a block written for another
table. `392` simulates every new block against every file in `data/clean`
BEFORE writing anything, and refuses the whole run on an unguarded capture. The
same simulation caught four tables sitting in a block that never described them
(`fr_consultation_referenced.csv` in `11_nagpra` at 0.80,
`bill_votes_entity_bridge.csv` in `06_nonprofit` at 0.60) and one decided by
ALPHABETICAL ORDER on a 0.737 tie.

**A FRAGMENT FILE NAME IS NOT A BLOCK KEY.** `05b_identifier_graph.csv` carries
three datasets and `16_digital_gaming.csv` carries four. Deriving ownership
from file stems misses sixteen live blocks, and would have had 392 create a
second fragment for a block that already lived inside somebody else's file —
`build()` concatenates both. Derive ownership from the `dataset` COLUMN.

**87's `SHIP RATE` WAS PRINTING 100.0% AND HAD BEEN SINCE IT WAS WRITTEN.**
`n_lost, _, _, _, _ = scan(...)` unpacked five values from an eight-value
return; the `ValueError` was swallowed by the `except` under it, `lost_rows`
stayed 0, and the rate was shipped-over-shipped. All **140** `NO_CODEBOOK` rows
of `dist/_ship_rate.csv` carried `rows = -1` and nobody looked. The one number
that script exists to expose was the one number it could not measure. Fixed by
taking element 0 BY INDEX and printing the failure instead of eating it. **The
next SHIP RATE will look far worse and will be the first true one.**

**Registering a block makes a table SHIPPABLE; it does not make it DOCUMENTED.**
642 columns across the 73 new blocks have no definition anywhere in the repo
and are written `published = 0`, `access_tier = internal`, with a description
that says so — the `pdf_path` disposition at scale. Eleven tables were
REFUSED outright because a block would have defined under 8 variables and
under 60% of their publishable columns; they are named with counts in
`docs/STAGED_SHIP_CHAIN_2026-08-26.md` Part 6. Never invent a definition to
clear a counter: a blank column is a question, a wrong one is believed.

**THE CHAIN IS STAGED, NOT RUN.** No quiet window opened. Live at every check:
`121_pull_subawards_api`, `317_cdx_tribal_vendor_hosts`,
`327_migrate_class7_keys_to_digests` (relaunched twice, writing keys in place),
`367_courtlistener_party_name_probe`, `384_crawl_uncrawled_open_properties`,
and up to three concurrent `62` runs. `data/clean` was last written 20:24:46,
inside the runbook's own 30-minute stop rule. Only step 1 was run —
`cedar_codebook.py build`, 2,798 -> 4,465 rows — because it writes one derived
file atomically and no data row. **`62` -> `87` -> `102` -> `110` -> `25` ->
`27` remain to be run, with the four stale notes contracts to delete
afterwards. Full instructions: `docs/STAGED_SHIP_CHAIN_2026-08-26.md`.**


### A DEFINITION AND A TIER MUST NOT CONTRADICT EACH OTHER (2026-08-26, script 392)

`identifier` is `access_tier = internal` in **eight** codebook blocks and
`public` in one, and its written definition begins *"WITHHELD from
publication."* `41_build_codebooks.access_tier("identifier")` nevertheless
returns `public`, because the bare name misses its `IDENTIFIER_COLS` regex.
The first run of `392` wrote it into the ledger block as **published, carrying
a description that says it is withheld**, and it would have shipped that way.

Two guards now stand in `392`, and the 73 fragments were deleted BY EXACT
FILENAME and rewritten under both:

1. **Unanimous inheritance.** 235 column names are tiered internal by EVERY
   block that carries them. That tier is inherited, never re-decided by the
   consumer - rule 1 at the top of this file, applied to the codebook itself.
2. **The contradiction guard.** A definition matching `WITHHELD` or
   `never publish` forces `internal` whatever the regex says. **The prose
   wins: somebody wrote it deliberately, and a regex did not.**

And one smaller trap paid for on the way: **a DRY RUN must not overwrite the
record of a REAL one.** `392 --check` rewrote its own report with
`blocks_written: []`, and the list of exactly which fragments it had created -
the only safe way to remove them by exact filename rather than by glob - was
gone. `--check` writes to a separate `_DRYRUN.json` now.

### NAMED GATE FAILURE — three lint instances, none of them this pass

`62` fails on `lint_new_defect_instances = 1` (20:36) and on `class2c 60 -> 62`
/ `class6 33 -> 34` (21:00). All three findings are other agents' scripts, two
of which were running at the time:

| finding | owner |
|---|---|
| `class2c 382_remine_property_site_corpus.py: stats["capacity_refused_implausible"] += 1` | the property-site re-mining pass (LIVE at 20:36) |
| `class2c 384_crawl_uncrawled_open_properties.py: stats["hosts_stopped_on_first_refusal"] += 1` | the open-property crawl (LIVE at 20:55) |
| `class6 98_build_oira_and_hearings.py: hearing_appearances.csv` | the OIRA/hearings build |

`class7` is **42 before and 42 after** — the tracked metric did not rise.
Neither `391` nor `392` appears in any `293` finding.
**Do not run `62 --baseline`.** Six sessions in a row buried every other
regression behind one line they had learned to scroll past.

---

## A SELF-PUBLISHED CLAIM IS A MEASUREMENT TYPE, NOT A CONFIDENCE LEVEL (2026-08-26, scripts 382–384)

Full log: `docs/GAMING_PROPERTY_SITE_REMINE_2026-08-26.md`. Everything below is
a rule paid for by something this pass measured.

**Two new `cedar_domain.MeasurementType` terms**, written on the
`GAME_FINDER_OBSERVATION` pattern — a comment saying what one row IS and IS NOT:
`SELF_PUBLISHED_MARKETING_CLAIM` (capacity off the operator's own site) and
`SELF_PUBLISHED_EMPLOYMENT_CLAIM`. **Both `is_observed`; both in
`NEVER_PROMOTES_TO_ACTIVE`.**

> **A regulator's count and a website's boast are different measurements of
> different things. They must never be summed, averaged, or silently
> preferred.** `is_observed` asserts somebody counted a real population on a
> real date. It does NOT assert the figure is exact, audited or current — that
> is what the measurement type and the bound columns are for.

Marketing copy carries three defects a regulator filing does not, and each is
recorded per row rather than argued about in prose: **puffery** ("over 1,500" is
a floor, not a value → `bound_direction`), **rounding** ("2,000 slot machines"
is never exactly 2,000), and **staleness with no date** (`as_of_date` is the
RETRIEVAL date, precision `observed_on_retrieval_date`).

**A number with no verbatim sentence is REFUSED at write, not downgraded.**

### THE FINDING THAT MOTIVATES THE WHOLE LAYER

**All 10,122 `metric = employees` rows in `gaming_facility_metrics.csv` come
from ONE source — the Casino City panel — across 323 facilities.** Measured
2026-08-26. That series is QA-reference-only and may never publish, so **Cedar's
per-property employment coverage in anything shippable is currently zero.** The
29 operator-published claims recovered here are the entire publishable layer.

### LATENT: `PROPERTY_REPORTED_COUNT` CAN BE PROMOTED AND SHOULD NOT BE

It is `is_observed` and **not** in `NEVER_PROMOTES_TO_ACTIVE`, so
`may_promote(PROPERTY_REPORTED_COUNT, ACTIVE_FLOOR_COUNT)` is `True` today.
Script `142` writes it on all 262 rows of
`gaming_property_site_observations.csv`, which are marketing sentences off
operator websites — exactly the material the two new types are barred from
promoting. **Nothing promotes anything today, so it is a latent hole, not a live
defect**, and closing it would change the meaning of a column another build
owns. Recorded in `cedar_domain.py` beside the sets. The fix belongs to 142's
owner: re-type those rows, and `PROPERTY_REPORTED_COUNT` goes back to meaning a
count a property REPORTED to somebody who asked, on a stated date.

### A SINGLE-REASON REFUSAL PILE IS A PARSER GAP UNTIL IT IS READ

All **1,621** rows of `review/gaming_property_site_refused_2026-08-12.csv`
carry the SAME reason. That records which guard fired and nothing about whether
it was right. Re-read: **305 distinct candidates → 231 RECOVERED, 45 confirmed
(now with 7 named reasons), 29 ambiguous.** Same shape as `IMAGE_ONLY_SCAN`
falling 264 → 1.

**And collapse to DISTINCT before adjudicating.** 1,621 rows are 305 sentences;
a build that writes one row per match occurrence multiplies every later verdict.
Reporting 1,621 recoveries would have been the additions-glob defect (class 1)
wearing a new hat. Both counts are reported.

**The single biggest gap was a one-WORD lookback.** 142 accepts a number only
when the immediately preceding word is a cue, so **an explicit bound qualifier
separated from the number by anything at all is invisible** — *"showcases **over**
350 slot machines"*, 128 of the 231 recoveries. Second biggest: **a counting cue
governs only the FIRST item of a list**, so *"more than 2,000 slot machines,
over 60 table games"* loses the second count.

### A DOMAIN THAT DOES NOT RESOLVE IS A FACT ABOUT THE OBJECT

**This is a new failure shape for `docs/PULL_DISCIPLINE.md`'s table.** curl exits
`6` (`Couldn't resolve host`) and 142's `fetch` reports it as `status 0` —
indistinguishable from a dropped connection. 384's first run **stopped itself
after 48 consecutive NXDOMAINs, reporting "the HOST LAYER is refusing"**, on a
perfectly healthy network, because the first properties in its frame are Alaska
bingo halls whose generated candidate domains simply do not exist.

> **Collapsing NXDOMAIN into "transport failure" makes the block detector
> useless in exactly the run where it is needed.** Return curl's exit code and
> type `6`/`51`/`60` as facts about the object.

**And DNS-pre-filter a generated candidate set.** 71 of the first 80 candidates
had no DNS record. `socket.getaddrinfo` is not an HTTP request, does not touch
the site, and is the politest possible ordering — a name with no record can
never be knocked on.

### THREE SENTENCE SHAPES THAT LOOK LIKE AN EMPLOYEE COUNT AND ARE NOT

Each produced a row that would have been wrong in a different way:

- **A job fair is labour demand.** *"accepting applications for more than 300
  positions"* (Talking Stick) — 142's own `LABOR_DEMAND_STATEMENT`.
- **An executive bio counts another company's staff.** *"During his time at The
  Resort at Pelican Hill, Maneesh led a team of 350"* (Valley View) — a false
  attribution with a correct citation.
- **A department is not a property.** *"300 employees carry out the natural
  resource protection, planning and management"* (KwaTaqNuk) — a tribal
  government department roster. A subset published as a total understates it
  invisibly.

### TWO MORE, BOTH ALREADY-KNOWN SHAPES IN NEW PLACES

- **`"Live Nation"` resolved as a tribal owner**, because the tribal-form token
  *Nation* sits inside a concert promoter's name. This is `core()` folding
  `indian` into *National Education Association*, a third time. **A token that
  makes a name a tribe in one string is a brand in another, and only an explicit
  list can say which.**
- **A soft hyphen split the word the parser needed.** `Approxi\u00admately 300
  employees` renders normally and defeats every `\bapproximately\b` pattern.
  Fold soft hyphens and zero-width joiners — that is punctuation folding, not
  identity folding.

### AND ONE IN THE ADJUDICATOR ITSELF, FOUND BY READING ITS OUTPUT

`str.find("200")` located the refused value **inside `5,200`** and every context
test then read the wrong neighbourhood and recovered a number that was never
there. A located number needs a real numeric boundary. **Thirty rows read one at
a time found it; no counter would have.**

---

## STRANDED DATA: THE 521,566 ROWS WERE 7 (2026-08-26, scripts 399/400/401)

`docs/SHIP_GAP_REPORT.json` reported **521,566 rows in `data/staging/` and
`data/interim/` "never promoted"** and **7,009 rows in 8 root CSVs "no registry
enumerates"**. Both were true inventories and neither was a gap, because both
were computed from **where a file SITS** and never from whether its **CONTENT
landed**.

> **A STRANDING AND A DUPLICATE LOOK IDENTICAL FROM THE OUTSIDE.** The only
> thing that tells them apart is a membership check against the promoted table
> **on a real key**.

`code/399_inventory_stranded_data.py` runs that check for every file, every
time, and writes `docs/stranded_data_inventory.json`. Full write-up with the
per-file reasoning: **`docs/STRANDED_DATA_DISPOSITION.md`**.

| disposition | files | rows |
|---|---:|---:|
| INTERMEDIATE-BY-DESIGN | 19 | 455,587 |
| ALREADY-LANDED | 19 | 71,394 |
| SUPERSEDED | 5 | 1,234 |
| LIVE-WRITER | 9 | 1,235 |
| NEEDS-A-RULING | 1 | 326 |
| **PROMOTED** | — | **7** |

**Four findings worth keeping:**

1. **A REFUSAL IS A RULING, AND `entity_id == ""` DOES NOT SAY WHICH.** 83
   corpus rows carried an exact name match to a current spine entity. **75 of
   them carried an explicit `refused_*` / `ambiguous_*` `resolution_basis`
   written by the producer.** Re-matching them is DEFECT 3 in a new coat —
   `Circle`, `Georgetown`, `Hamilton` and `Enterprise` are Alaska Native village
   names that are also ordinary English words, `FirstBank` is a CDFI, and `DC)`
   is a fragment of an address. Only `no_spine_match` is a real stranding, and
   it means one thing: **the spine did not hold the entity when the build ran.**
2. **`[^a-z0-9]` IS A CASE-SENSITIVE CHARACTER CLASS AND READS AS AN
   INSENSITIVE ONE.** A normaliser written `re.sub(r"[^a-z0-9]+", " ", s).lower()`
   — casefolding AFTER the strip — turns `AARP Foundation` into `oundation`,
   which collides with a spine alias. The dry run proposed publishing **AARP,
   UPS, TD Bank and POPVOX as Native entities, 29 rows, every one
   confident-looking.** Casefold FIRST. **This is why a promotion gets a
   `--dry-run` that prints every row by name before `--apply` exists.**
3. **A MODULE-LEVEL LINT FINDING WAS STRUCTURALLY UNWAIVABLE.**
   `293`'s `detect_class6` reports at **line 1** — the finding is about the FILE
   — and `apply_waivers` walks *upward* from the flagged line, so it started at
   line 0 and stopped. Line 1 is the shebang, so no waiver could be written
   there either. **Every class-6 finding in the project could be detected and
   none could be answered**, while the class-6 write-up above explicitly asks
   for "the ordering has to be written down by a person". Fixed: for a line-1
   finding only, the module's leading comment block is scanned downward.
   Detection is unchanged; waivers stay counted and named.
4. **A REPORT NAMES A SETTLED CASE AMONG UNSETTLED ONES AND TEACHES SKIMMING.**
   `160`'s root-CSV section printed `deals_2026_ytd.csv` and
   `deals_historical_2020_2025.csv` under "no registry enumerates the root" —
   **both had been DECLARED parts in `cedar_domain.PROMOTED_TABLES` since the
   deals repair.** The declaration and the glob never met. Six root files are
   now declared; the seventh was a review queue and went to `review/`.

### GATE FAILURES AT HANDOFF THAT ARE NOT THIS SESSION'S — NAMED, WITH OWNERS

Standing rule 15 response 3. Both appeared **between two consecutive runs of
`62`** in this session, from concurrent agents, and both are the cheap local
registration fix:

| failing metric | owning file / script | what has to happen |
|---|---|---|
| `ship_tables_at_zero` 138→139, `tables_missing_from_25_TABLES` 234→235, `tables_missing_from_27_SPEC` 249→250, `tables_missing_notes_contract` 139→140 | `data/clean/cedar_entity_identity_crosswalk.csv` (10,107 rows), written by **`code/417_build_entity_identity_crosswalk.py`** at 21:02 | register the codebook block, then re-run the full 7-step ship chain (`py -3 code/build.py ship`; “87 → 25 → 27” is a 3-step shorthand that omits the codebook build, the gate, the coverage profile and the harmonised views) per `docs/SHIPPING_RUNBOOK.md` |
| `lint_class6` 33→34 (`entity_aliases.csv`) | **`code/418_build_entity_alias_layer.py`** enriches in place a file **`code/97_build_aliases_and_relationships.py`** full-rebuilds | write the ordering into 97's header and waive it there — the waiver now works at line 1, see finding 3 above |

**One `62` handoff item is this session's and is already answered:**
`hearing_appearances.csv` gained a class-6 pair (`98` rebuilds it, `400`
enriches it). The ordering is written into `98`'s docstring under **RUN ORDER**
and waived there with a reason. **If `98` is ever re-run, run `400` after it.**

### DO NOT RE-INVESTIGATE THESE

- **The OIRA / hearings corpora (189,111 rows) are not a gap.** `98`'s own
  source says so: *"THE PUBLISHED FILE IS THE NATIVE SLICE. THE CORPUS IS
  CONTEXT."* Publishing the corpus ships non-Native rows as a Native product.
- **`subaward_uei_netnew_2026-08-05.csv` is still not subawards.** 252,078 rows,
  252,078 distinct `uei`, 8 columns — a DIMENSION table. Re-verified.
- **The gaming-employment staging pair is fully landed**, 2,046 + 502, and the
  71 rows absent from the promoted table are **exactly** the 71 that `262`
  withdrew as NOT_NATIVE. **Re-promoting them would republish a Delaware
  racino's Form 5500 as tribal.**
- **`bgov.csv` landed: 878 of 878 CAGE codes.** The ledger holds the value in
  `identifier`, **not** in a `cage_code` column — a check aimed at `cage_code`
  returns **0 of 878** and reads as a total stranding. That is defect 2b, and it
  produced one wrong conclusion in this session before it was caught.


### FOUR REGISTRY METRICS ROSE BY EXACTLY ONE, AND IT IS ONE TABLE (2026-08-26 21:15)

Between the 21:00 and 21:15 `62` runs, `ship_tables_at_zero` 138 -> 139,
`tables_missing_from_25_TABLES` 234 -> 235, `tables_missing_from_27_SPEC`
249 -> 250 and `tables_missing_notes_contract` 139 -> 140. `62` names the cause
in its own output:

    NEW TABLES AT A 0% SHIP RATIO (1), not in the shipping baseline:
      - cedar_entity_identity_crosswalk.csv (10,107 rows)

**One table, landed by another agent mid-session, moved four MUST_NOT_RISE
counters at once**, because four separate registries each notice the same
absence. It also took `ship_ratio_pct` 86.917 -> 86.811 - the warehouse grew,
the shelf did not. Over the same window `tables_missing_codebook_block` fell
**139 -> 69** on the 73 blocks registered by 392, so the two movements are
opposite in direction and must not be read as one number.

`391_triage_unshipped_tables.py` refuses to call the triage complete while any
table with rows has no verdict, names it, and exits non-zero. **Whoever built
`cedar_entity_identity_crosswalk.csv` should rule it** - and note that
"extract the entity crosswalk as a standalone deliverable" is the one thing
`87_build_dataset_notes.TERMS` forbids a subscriber to do, so SHIP is not the
obvious answer.

## NAMED GATE FAILURE — not mine, owner identified (2026-08-29, ~03:55)

Per standing rule 15 option 3, by **workstream C** (release replay, F13).

`62_no_regression_check.py` FAILS on one metric:

    !! sem_entities_uid_reassigned = 1, must be 0

    SEMANTIC CHANGES since the baseline (1 named of 1 total):
      UID REASSIGNED  AKNF-ACSRMT-00-CALSTA-ASVCPR
                      was: CE-00001-6S
                      now: CE-00002-CJ

**Owner: whoever is running `code/503_identity.py` this pass — workstream D**,
which owns that file in `docs/ARCHITECTURE_DECISIONS.md`'s ownership table.

Evidence, not inference:

- `data/spine/cedar_identity_register.csv` was rewritten at **03:54:14** today
  and now carries a **new column, `register_status`**. That column is written
  in exactly one place: `code/503_identity.py:795` (`"register_status":
  "active"`), 814, 859, 873, 893.
- `code/503_identity.py` is MODIFIED in the working tree, so this is live work,
  not abandoned work. Re-minting another agent's in-flight register would race
  it, and the register is the one data file git tracks precisely because a
  silent change to it must never be undetectable.
- The register's diff is 1,537 lines replaced. The gate reports **1** uid
  reassigned rather than all 1,536 rows the register then held (**1,555**
  today), so this is not (yet) a mass re-key — but the
  `minted` date on the moved row is **2026-08-29**, i.e. re-minted today.

**What has to happen:** workstream D either (a) shows the reassignment is
intended and re-records the semantic baseline WITH a written reason — the
gate's own note says *do NOT re-record the baseline until you know why* — or
(b) restores `AKNF-ACSRMT-00-CALSTA-ASVCPR` to `CE-00001-6S`. A uid that moves
is the single thing the identity contract promises cannot happen ("the uid
never changes" is written into every row of that register's own
`class_since_basis` column), and 1,555 uids are stamped across 125 tables (1,536 until 19 IHS self-governance consortia were promoted 2026-09-01).

Workstream C did not write to `data/spine/`, did not run `503_identity.py`, and
touched only `code/516_release_manifest.py`, `code/build.py`,
`docs/RELEASE_REPLAY_LOG.md`, `docs/releases/` and the untracked
`data/_release_inputs/` store. `62` exited **0** earlier in this same session
(03:38) and this metric was green then; it went red after 03:54.

**Follow-up, same session, and it is the more important finding.** The gate
did not settle — it OSCILLATED, and which metric fails depends on the second
you run it:

| run | result |
|---|---|
| 03:38 | exit 1 — `handoffs_failed_verification = 1` |
| ~03:45 | exit 0 — `no regressions` |
| ~03:55 | exit 1 — `sem_entities_uid_reassigned = 1` |
| ~04:00 | exit 0 — `no regressions` |
| 04:01 | exit 1 — `sem_facts_winner_changed 7,572` / `sem_facts_status_changed 1,504` / `sem_facts_removed 10,087` |
| 04:03 | exit 1 — back to `sem_entities_uid_reassigned = 1` |

Between those runs `data/clean/cedar_resolved_facts.csv` was rewritten (03:44 →
04:00) and then reverted to its 03:44 mtime, and
`data/spine/cedar_identity_register.csv` gained a column. Nothing workstream C
did touches either file.

**The gate is not lying and it is not broken. It is measuring a tree that four
workstreams are writing at once.** A MUST_NOT_RISE metric compares against a
baseline that assumes one writer, and the parallel pass broke that assumption
without anyone deciding to. Two consequences, both for the integrator:

1. **"62 exits 0" is not a durable claim during a parallel pass.** Any handoff
   whose verify commands include `62` will pass or fail on timing. That is the
   same self-reference the gate already carves out for
   `handoffs_failed_only_on_this_gate`, one level up.
2. **A release capture has the same problem**, and it is now measured rather
   than argued: `516_release_manifest.py build --all` re-hashes every input at
   the end and reported `quiescent: false`, naming
   `cedar_resolved_facts.csv` and `_correction_scan_cache.json` as rewritten
   mid-capture. See `docs/RELEASE_REPLAY_LOG.md` §4b and gated debt **D9**.

**What has to happen:** the integrator serialises the identity/assertion layer
work (`503_identity.py`, `510_assertions.py` — workstream D) against gate runs,
or declares a freeze window before the gate and before any release capture.
Whoever re-records the semantic baseline should also confirm
`AKNF-ACSRMT-00-CALSTA-ASVCPR`'s uid is the one the register is meant to
carry — the register's own `class_since_basis` column promises, in every row,
that *the uid never changes*.

---

### THE `identity_facts_legacy_only` RATCHET IS INSTALLED BACKWARDS (2026-08-31, workstream F)

Named here because standing rule 15 requires a failing gate line to be named
with its owner rather than stepped around. **`62_no_regression_check.py` is
the integrator's file this pass; workstream F did not edit it.**

`identity_facts_legacy_only` — identity-critical facts standing on a row with
no recorded provenance — is listed in **`MUST_NOT_FALL`**, under a comment
that reads, in the same three lines:

```python
    # External review finding 3: identity-critical facts standing on a row
    # with no recorded provenance. This may only fall.
    "identity_facts_legacy_only",
```

`docs/EXTERNAL_REVIEW_RESPONSE.md` records the intent explicitly: *"That
number is now a gated metric (`identity_facts_legacy_only`, MUST_NOT_RISE) so
the exposure can only shrink."* As installed, the gate does the opposite: it
**fails the build every time the exposure is paid down**, which is the one
thing external review findings F3/F4 asked for.

It fired on 2026-08-31 the first time anything reduced it:

```
!! identity_facts_legacy_only FELL 4,100 -> 4,089
```

The 11 rows are `entity.state` facts that gained a second, IRS-sourced
assertion and moved from `legacy_only` to `traceable_single_source`. Nothing
was removed — `sem_facts_removed = 0` on the same run.

**Fix (integrator, one line):** move `"identity_facts_legacy_only"` from
`MUST_NOT_FALL` to `MUST_NOT_RISE`. Do **not** re-record the baseline to clear
it — the file's own words: *"--baseline is a floor, not an acknowledgement
button"* — because that would fix the floor at 4,089 and fail the next payment
in exactly the same way.

**Also failing on that run, and NOT workstream F's:** `lint_class7` 42 → 46,
`lint_bug_class_instances` 147 → 151 and `lint_new_defect_instances` = 4. All
four new instances are named by 293 in **`code/512_build_dataset_contracts.py`**
(`hash("\x1f".join(parts))` and three siblings) — workstream **E**'s file this
pass, modified mid-session. Owner: E.

---

## NAMED GATE FAILURE - `ship_dist_rows` and `lint_class6`, owners identified (2026-08-29, nagpra closure)

Recorded under standing rule 15 option 3 - name the failing metric, the owning
file and what has to happen - by the **nagpra closure agent**. `62` was **exit
0** when this pass began and is **exit 1** at its end on three lines, **none of
which this pass produced**. The arithmetic that proves it is below, because
"not mine" without arithmetic is exactly what rule 15 forbids.

```
!! lint_new_defect_instances = 2, must be 0
!! lint_bug_class_instances  ROSE 147 -> 148
!! lint_class6               ROSE  30 ->  31
!! ship_dist_rows            FELL 8,463,001 -> 8,461,252
!! ship_ratio_pct            FELL 99.774% -> 99.773%
```

**1. `lint_class6` +1 / `lint_new_defect_instances` = 2. OWNER: the
`federal-register` closure workstream, and both instances have the SAME
cause.** 293 names the rebuild side, which is misleading here; 293's own
`class6_io_map` names the new writer:

    federal_actions.csv                    rebuild 11_classify_federal_actions.py
                                           enrich  519_closure_federal_register.py
    fr_ex_parte_party_entity_links.csv     rebuild 154_build_fr_ex_parte_notices.py
                                           enrich  519_closure_federal_register.py

`code/519_closure_federal_register.py` is UNTRACKED and was created this
session. It is the in-place enricher on both pairs, so both findings arrived
with it. **Declaring the pair in `cedar_pipeline.KNOWN_ORDERINGS` will NOT
clear this** - `detect_class6` builds its map from the io scan alone and never
reads that list. **WHAT HAS TO HAPPEN:** that workstream either makes 519 merge
rather than write those two tables, or waives each line in 519 with
`# lint-ok: class6 - <reason>`, then `py -3 code/293_lint_bug_classes.py
--baseline`.

No nagpra table is in the class6 set: `nagpra_notices.csv`,
`nagpra_notice_entity_bridge.csv` and `fr_nagpra_title_index.csv` each have
exactly one rebuilder and no enricher in that same map, and
`cedar_harvest_conservation.csv` - which the nagpra builders now MERGE into -
has no rebuilder at all, so it forms no pair.

**2. `ship_dist_rows` -1,749. OWNER: the `contractors` closure workstream.**
`prime_contracts_entity_year.csv` was deliberately collapsed from **8,464 rows
to 6,715** this session - the entity-year regrain recorded in that agent's own
`code/512_build_dataset_contracts.py` block ("the four-column key and the
two-column key sum to the IDENTICAL cent"). 8,464 - 6,715 = **1,749**, the
exact fall. This is intended work, not a loss: the metric is MUST_NOT_FALL
because there is normally no benign cause, and a deliberate regrain is the
benign cause it does not know about. **WHAT HAS TO HAPPEN:** that workstream
re-publishes the dist artefact for the regrained table, or records the regrain
where the shipping metric can see it. Do NOT re-baseline to clear it.

`nagpra`'s own contribution to the shipping metrics this pass was **positive**:
`fr_nagpra_title_index.csv` 6,606 -> 6,644 rows (a strict superset; the shipped
copy predated its own input by 20 days). No nagpra table shrank, and the two
large ones are byte-identical to their previous release.

## NAMED GATE FAILURE — the `ship_dist_rows` item is mine, and an agent cannot clear it (2026-08-29, correctness pass)

The nagpra closure agent's entry above correctly attributes the **-1,749** on
`ship_dist_rows` to the contractors correctness pass. It is mine. Here is the
accounting it asked for, and the reason "re-publish the dist artefact" does not
work.

**The arithmetic closes exactly, and the builder refuses to write unless it
does.** `py -3 code/428_rebuild_prime_entity_year.py` prints, on every run:

```
rows before                                       8,464
- surplus name/tier variants of a key that still exists  -1,751
+ (tribe_id, fiscal_year) keys that did not exist before     +2
- keys that EXISTED before and do not now                    -0
rows after                                        6,715
reconciles: 8,464 - 1,751 + 2 - 0 = 6,715  EXACT
```

and raises `SystemExit` if any entity-year present before is absent now, or if
the arithmetic does not close. **No entity-year was lost and no dollar was
lost** — the total is $244,765,639,853.91 against $244,765,639,853.98 of
attributed row dollars, inside the derived cent-rounding bound. The +2 keys and
+$483,461.85 are rulings 174/427/64 that had been applied to
`prime_contracts.csv` and never cascaded to the panel; the panel had been
shipping pre-ruling numbers.

**Why re-publishing dist does not clear it.** `62.ship_dist_rows` is
`Σ min(dist_rows, clean_rows)`. The clean file legitimately holds 1,749 fewer
rows, so the min is 6,715 whether dist is refreshed or not. Any correct regrain
of a shipped table moves this metric down and nothing an agent may run moves it
back.

**Why the sanctioned allowance does not clear it either — and this is a real
gate defect worth someone's attention.** `62` allows a `ship_dist_rows` fall
when the correction register declares `rows_removed` **exactly equal to the
fall**, but it compares against `sum(declared_removals.values())` — the sum of
every removal ever declared. The register already carries 55 rows from the
lobbying episode, which the current baseline has absorbed. Declaring 1,749 makes
the sum 1,804 against a fall of 1,749, so it can never match. **The allowance
works exactly once.** Twenty lines further down in the same file the per-file
form of the same allowance is written correctly (`dec = declared_removals.get(f)`
compared against that file's own fall). The aggregate check should use the same
shape. `62` is owned and was not edited; no register row was written, because
writing one that cannot match would only add noise to a MUST_NOT_RISE
propagation check.

**WHAT HAS TO HAPPEN:** the integrator either fixes the aggregate allowance to
be per-table and consumable, or re-records the baseline now that the collapse
is verified and reconciled. Written up as §8a of
`review/OWNER_DECISION_QUEUE.md`. Do not re-baseline to hide it; re-baseline
because the fall is proven benign.

**`lint_class6` +1 and `lint_new_defect_instances` = 2 are NOT mine, and the
nagpra entry above names the owner correctly** — `code/519_closure_federal_
register.py`, the federal-register workstream. Confirmed independently from
293's own `class6_io_map`: it is the sole enricher on both
`federal_actions.csv` and `fr_ex_parte_party_entity_links.csv`, and both
findings appeared with it. This pass moved class6 the other way: restoring the
transaction key and the panel regrain left `prime_contracts.csv` and
`prime_contracts_entity_year.csv` with no wholesale rebuilder at all, which
removed one finding.

---

## 2026-09-01, workstream J (spiderweb harvest) — a red gate that is NOT mine, named

`62_no_regression_check.py` fails on six MUST_NOT_RISE metrics
(`ship_tables_at_zero`, `tables_missing_codebook_block`,
`tables_missing_from_25_TABLES`, `tables_missing_from_27_SPEC`,
`tables_missing_notes_contract`, `tables_undocumented_in_codebook`, each +1).

**Cause and owner:** `data/clean/cedar_dataset_punchlist.csv` (418 rows,
written 16:41) — a NEW unregistered table produced by
`code/526_dataset_standard.py`, which is not workstream J's file and did not
exist when this pass started. All six metrics rise by exactly one, which is
what one unregistered table in `data/clean` does.

**Proved, not asserted:** the file was moved aside and the gate re-run with
every one of J's changes still in place. Result: **`no regressions`, exit 0.**
The file was restored immediately.

**What has to happen:** whoever owns `526` registers a codebook block for
`cedar_dataset_punchlist.csv` (or declares it INTERNAL), then re-runs
87 -> 25 -> 27 per `docs/SHIPPING_RUNBOOK.md`.

J's own outputs are in `review/`, which 62 correctly does not scan, precisely
so that a candidate queue cannot move a shipping ratchet.

---

## GATE FAIL 2026-09-01 16:45 — NOT the ruling-mining workstream. Owner named.

Recorded under standing rule 15 option 3 by **workstream I** (ruling mining:
`code/522_mine_rulings.py`, `code/503_identity.py` loose-path guards,
`docs/RESOLUTION_RULES_LEARNED.md`, `docs/NATIVE_ENTITY_NUANCES.md`).

**The failing metrics, all six of them one event:** `ship_tables_at_zero`
13→14, `tables_missing_codebook_block` 3→4, `tables_missing_from_25_TABLES`
179→180, `tables_missing_from_27_SPEC` 194→195, `tables_missing_notes_contract`
14→15, `tables_undocumented_in_codebook` 3→4. `ship_tables_total` rose 213→214:
**exactly one new table landed in `data/clean/` and it is undocumented.**

**Owner: `code/526_dataset_standard.py` / `code/518_dataset_readiness.py` — the
dataset-standard workstream.** The table is
`data/clean/cedar_dataset_readiness.csv`, created 16:31 today, and those are
the only scripts that write it. The remedy the gate prescribes (write a
codebook block, then `87 → 25 → 27`) belongs to that workstream.

**Proven not to be workstream I.** This workstream created exactly one file,
`data/interim/ruling_corpus_mined.csv`, which is in `interim/` and is therefore
outside every shipping metric — `62`'s own output never names it. Its only
`data/clean/` interaction is read-only. The `503` guards added this pass change
no table: they alter `resolve()`, which is not run with `--apply` here, and
`503 reconcile` moved by one legacy id carrying **$0**
(`ONONDAGA COUNTY RESOURCE RECOVERY AGENCY INC`, correctly refused).

**Two earlier failure sets in the same hour, both also other workstreams', both
already gone by 16:45** — `lint_class2b` +1 (`524_universe_gap.py`),
then `files_with_columns_lost_vs_backup` = 1 with `lint_class2c` +1
(`fpds_uei_edges.csv` against `.bak_2026-09-01_pre523_source_expansion`, and
`13_build_fpds_hierarchy.py`; the spiderweb workstream, `523`). Three
completely different regression sets from three consecutive runs of an
unchanged gate. This is the phenomenon the 2026-08-26 19:10 entry above already
names — *a gate that reads a shared directory mid-write reports another
agent's incomplete step as a regression* — and on a parallel-workstream day it
is the normal case, not the exception. **Compare file creation times against
the live workstreams before believing a `62` failure is yours.**

## GATE FAIL 2026-09-01 — the shard program launch. One line IS mine; the rest named.

Fourteen workstreams were live when this gate ran (nine entity shards A–I, plus
subawards, gaming, lobbying, natural-resources and TERO acquisition). Per the
2026-08-26 19:10 entry and the note directly above, **a gate reading a shared
directory mid-write reports another agent's incomplete step as a regression**,
and on a day like this that is the normal case. Attribution below, not a shrug.

### MINE, AND FIXED IN THE SAME PASS

`code_duplicate_numbers` 43 → 44. I named the shard consolidator
`532_shard_consolidate.py`; shard E independently claimed 532 for
`532_shard_e_anc_web_probe.py`, mid-flight, as part of a coherent 531/532/533
block. **Renamed mine to `528_shard_consolidate.py`** (528 and 529 were free)
and updated every reference in `docs/SHARD_PROGRAM.md` and
`docs/SHARD_COVERAGE.md`. Shard E's block was left untouched — it is running.

The general lesson, since this will recur every time agents are launched in
parallel: `ls code/<n>_*` is not sufficient when other agents are *concurrently*
choosing numbers. Whoever is still running keeps the number; the integrator moves.

### NOT MINE — named, with owners

| line | owner | what |
|---|---|---|
| `files_with_columns_lost_vs_backup` = 1 | `144_build_admin_appeals.py` | see below |
| `lint_class1` 0 → 2 | `531_shard_e_anc_report_mine.py` (shard E) | two `glob.glob` calls |
| `lint_class2c` 60 → 62 | `144_build_admin_appeals.py`, `344_pull_nigc_document_surface.py` (gaming) | silent skip counters |
| `lint_class4` 9 → 12 | `221_probe_regulations_gov_comments.py` (lobbying), `532_shard_e_anc_web_probe.py` (shard E), `shard_d_web_probe.py` (shard D) | deadline/budget breaks |
| `lint_class5` 6 → 7 | `shard_c_tribe_web_probe.py` (shard C) | `if key in done` resume guard |
| `ship_*`, `tables_missing_*`, `tables_undocumented_in_codebook` +2 each | the 2 new tables listed under NEW TABLES AT A 0% SHIP RATIO | new tables, not yet in the codebook |

Every one of these agents was briefed to finish with `62` exit 0, so these are
theirs to clear before handoff. They are recorded here so the next session does
not re-diagnose them, and so no one records them as "pre-existing, not mine."

### THE ONE WORTH READING — a hub key was dropped, quietly

`admin_appeal_positions.csv`, re-derived today by `144_build_admin_appeals.py`:

- rows **1 → 8** (real growth, good)
- **added** `record_scope`, `record_scope_basis`, `inclusion_basis`,
  `derivation_basis` — correct ADR-010 / ADR-013 work, all 8 rows
  `multi_entity` / `named_entity`
- **dropped `cedar_uid`**, which the backup had populated

`native_entity_id` is still populated 8 of 8, so the identity is not lost — but
the **hub key column is**, and C4 attachment is measured on `cedar_uid`. A
re-derive that adds the new ADR columns while dropping the one that attaches the
table to dataset 13 is a hub-and-spoke regression wearing the costume of an
upgrade, and it is invisible unless something diffs against the backup.

Not repaired here: `144` is another workstream's file and `cedar_uid` is
resolver output, so restoring it by mapping `native_entity_id` in a utility
script would be exactly the unsourced identity write `503`/`510` exist to
prevent. **Owner of 144: re-add `cedar_uid` through the resolver, not by hand.**

Generalisable, and the reason this is written up rather than just fixed: an
enricher that rewrites a table wholesale will silently drop any column it does
not know about. This is the class-6 shape that destroyed the conservation ledger
on 2026-09-01 (see `510_assertions.py`), now in a different file. **A rebuild
writer on a table other scripts enrich must preserve unknown columns, or the
gate's backup diff is the only thing standing between us and silent loss.**

## GATE FAIL 2026-09-01 — natural resources (workstream O). None of it is mine; owners named.

`py -3 code/62_no_regression_check.py` exits 1. **Not one failing line is a
natural-resources file or table.** Standing rule 15 option 3: named, with
owners, rather than recorded as "pre-existing" and stepped around.

*FOUR consecutive runs of the unchanged gate produced four DIFFERENT
regression sets, because fourteen workstreams were writing `code/` and
`data/clean/` throughout. The table below is the 19:52 run. The final run,
after this workstream's last edit, reads: `lint_class2b` +1
(`shard_f_membership.py`), `lint_class2c` +1
(`344_pull_nigc_document_surface.py`), `lint_class5` +2
(`547_shard_c_hidden_endpoint_sweep.py`, `shard_g_newsletters.py`),
`tables_missing_from_25_TABLES` and `tables_missing_from_27_SPEC` +1 each.
`code_duplicate_numbers` had cleared by then — somebody renamed. The sets are
different every time; the ownership conclusion is the same in all four, and
`files_with_columns_lost_vs_backup` is **0** in all four.*

| line | owner (named by `62`/`293` itself) | what |
|---|---|---|
| `code_duplicate_numbers` 43 → 44 | the shard workstreams | a new script reused a taken number. **Not this workstream: it created no script.** The only file it edited is `code/83_build_resource_ledger.py`, which already existed |
| `lint_class2b` 0 → 1 | `shard_f_membership.py` (shard F) | |
| `lint_class2c` 60 → 61 | `344_pull_nigc_document_surface.py` (gaming) | `skipped += 1` silent counter |
| `lint_class5` 6 → 7 | `shard_g_newsletters.py` (shard G) | `if uid in done:` resume guard |
| `lint_new_defect_instances` = 3, `lint_bug_class_instances` 146 → 147 | the three above | roll-up of the same three |
| `tables_missing_codebook_block`, `tables_missing_from_25_TABLES`, `tables_missing_from_27_SPEC`, `tables_undocumented_in_codebook` | native-owned businesses (`native_owned_businesses.csv`, 2,393 rows) and four other new tables that appeared and were registered between runs | new `data/clean/` tables with no codebook block |

**Proven not to be workstream O.** `293_lint_bug_classes.py` reports **zero**
hits in `code/83_build_resource_ledger.py`, the only script this workstream
edited. No new `data/clean/` table was created — every row landed in
`resource_revenue.csv` and `resource_parties.csv`, both already in the
shipping baseline and the codebook.

### The one line that WAS mine, and it was fixed before this run

`files_with_columns_lost_vs_backup` is **0**. It was 1 earlier today
(`144_build_admin_appeals.py`), and this workstream came within one command of
adding a second: `83_build_resource_ledger.py` writes with a DECLARED field
list and `extrasaction="ignore"`, so its first append run rewrote
`resource_revenue.csv` from **41 columns to 40** and deleted `cedar_uid` from
10,482 rows. Row count unchanged, no error, no warning.

The declared field list is a contract for the columns a script FILLS. It was
never a licence to delete another script's. Fixed with `fields_preserving()`,
which unions the declared list with whatever the published header already
carries, and every write in the file now routes through it. **This is the
class-6 shape the entry directly above this one describes, in a fifth file** —
a rebuild writer on a table other scripts enrich must preserve unknown columns.

### The measured-not-failed line that IS natural resources

`resource_revenue.csv` grew **10,482 → 11,305** this pass and `dist/` has not
been rebuilt, so ~823 of the 5,035 `ship_unshipped_rows` are its. **That is the
integrator's step** — `build.py ship --execute` is outside this workstream's
permissions — and it is expected, not a defect. `ship_ratio_pct` is 99.941 and
did not fall on this run.

## GATE FAIL 2026-09-01 19:40 — NOT shard J. One line WAS mine and is fixed; the rest named.

Recorded under standing rule 15 option 3 by **shard J** (990 mission-text
mining: `code/541_shard_j_mine_990_mission_text.py`,
`data/staging/np_mission/`, appended item 12 in
`review/OWNER_DECISION_QUEUE.md`). Shard J writes nothing to `data/clean/`,
`data/spine/` or `code/` beyond that one new script.

### MINE, AND FIXED IN THE SAME PASS

`lint_class2c` 60 → **62** on the first run, of which one instance was
`541_shard_j_mine_990_mission_text.py - sc["returns_with_mission_text"] += 1`.
It is not a drop counter at all — `DROP_WORD` in `293_lint_bug_classes.py`
matches **`miss` inside the word `mission`**. Renamed the key to
`returns_with_purpose_narrative`; the instance is gone and `class2c` is back to
61, the one remaining instance being `344`'s (below). Worth knowing for anyone
else mining 990 text: **a counter with "mission" in its name trips class2c.**

### NOT MINE — named, with owners (state at 19:40)

| line | owner | what |
|---|---|---|
| `code_duplicate_numbers` 43 → 44 | shard C and shard D | `547_shard_c_hidden_endpoint_sweep.py` and `547_shard_d_web_probe.py` both claimed **547**, concurrently. Per the launch entry above, whoever is still running keeps the number. `541` is unique and is shard J's. |
| `lint_class2b` 0 → 1 | `shard_f_membership.py` (shard F) | computes a share and reads columns by name without an existence check |
| `lint_class2c` 60 → 61 | `344_pull_nigc_document_surface.py` (gaming) | `skipped += 1` naming nothing |
| `lint_class5` 6 → 7 | `shard_g_newsletters.py` (shard G) | `if uid in done` resume guard |
| `tables_*` +1 / +5 each, `tables_undocumented_in_codebook` 3 → 4 | see below | new undocumented tables in `data/clean/` |

Nine `data/clean/*.csv` files were written by other workstreams during this
pass alone: `admin_appeal_positions.csv`, `codebook_master.csv`,
`native_owned_businesses.csv`, `nonprofit_schedule_c_coverage.csv`,
`nonprofit_schedule_c_lobbying.csv`, `regulations_gov_comments.csv`,
`regulations_gov_entity_coverage.csv`, `resource_parties.csv`,
`resource_revenue.csv`. `ship_tables_total` 213 → 218. **None is shard J's** —
shard J's five outputs are all under `data/staging/np_mission/`, which `62`
does not scan.

Also worth recording: between shard J's baseline run at 19:05 and this one,
`lint_class1` fell 4 → 0 and `lint_class4` fell 12 → 9 as shard E and shards
C/D/G cleared their own instances, while `class2b` and `class5` appeared fresh.
**Three different regression sets from three runs of an unchanged gate in
thirty-five minutes.** Compare file creation times against the live
workstreams before believing a `62` failure is yours — the entry above already
says this and it held again.

### A FINDING, not a gate line — two workstreams built Schedule C in parallel

`data/clean/nonprofit_schedule_c_lobbying.csv` (6,870 rows, 19:20, the lobbying
workstream) and `data/staging/np_mission/schedule_c_lobbying.csv` (860 rows,
shard J) were built within the same hour from the same corpus, and they are
**complementary, not duplicates**:

* the clean table enumerates every return in `irs990_schedc/` (6,870) and marks
  which carry a Schedule C;
* shard J's staging table scans **all three** local 990 directories and finds
  **860 returns that actually contain a Schedule C — 475 in `irs990_schedc/`,
  376 in `irs990_grantee/`, 9 in `irs990_grantmakers/`.** The 385 outside the
  schedc directory are invisible to a dir-scoped pull.
* shard J's also carries the **314 `ExplanationTxt` narrative blocks (166 KB)**
  in which filers describe their lobbying in prose, read from the Schedule C
  subtree only — the same tag carries Schedule O narrative everywhere else in a
  990 and scooping it up would report general supplemental text as lobbying.

Whoever owns the clean table should fold in the other two directories and the
narrative before this ships. Shard J did not touch it.

### AND A REAL UNDERCOUNT IN AN EXISTING SCRIPT

`code/99_build_earmarks_and_schedc.py` appends 30 `schedc_*` columns to
`np_financials.csv` and records `schedc_present = 1` on **93 rows** with a
lobbying total of **$82,303**. Measured against the same local corpus, 860
returns carry a Schedule C. Two causes: it reaches a narrower slice than what is
on disk, and `schedc_total_lobbying` reads only the 501(h) `...Grp` shape, so
the **245 non-electing filers** who report a flat `TotalLobbyingExpendituresAmt`
are all read as zero. That is a defect, not a coverage limit. Owner of 99.

## GATE FAIL 2026-09-01 — shard D. Two lines were mine; both fixed. Rest named.

Recorded under standing rule 15 by **workstream SHARD-D** (tribes with a gaming
facility, `tribe_id` sorted, rows 214–284; `code/553_shard_d_web_probe.py`,
`data/staging/tribe_web_map/shard_d.csv`,
`data/staging/tribe_harvest/shard_d/`).

### MINE, AND FIXED IN THE SAME PASS

| line | what | fix |
|---|---|---|
| `lint_class4` 9 → 10 | `if time.time() > RUN_DEADLINE: break` in my probe, in a file that writes the completion word `FETCHED`, with no comparison of retrieved against the total the run was asked for | the probe now computes `expected_total` (candidate rows in the file), counts `attempted_this_run` and `unattempted_after_deadline`, writes `coverage_complete` and **returns exit 3** when the deadline truncated it. A deadline-truncated run can no longer be read as complete coverage of a slice. Verified: 293 reports no `shard_d` finding. |
| `code_duplicate_numbers` 43 → 44 | I named my probe `547_shard_d_web_probe.py`; shard C had concurrently claimed 547 for `547_shard_c_hidden_endpoint_sweep.py` | **renamed mine to `553_shard_d_web_probe.py`** (548–553 were all free; took the top of the free block to leave room for the agents still choosing). Shard C keeps 547 — it is running. Same lesson as the launch entry above: `ls code/<n>_*` is not sufficient when agents choose numbers concurrently. |

A `lint_class5` finding also appeared on my probe mid-pass (`if key in done:`
resume guard, in a file that rewrote a run-state JSON wholesale). Fixed properly
rather than waived: the run state is now **appended** to `_run_state.jsonl`, so a
later run that skips everything already on disk cannot overwrite the run that did
the fetching with a zeroed summary. This is the same principle as
`PULL_DISCIPLINE.md`'s "a shared lock field must not be ambiguous".

### NOT MINE — named, with owners

| line | owner |
|---|---|
| `lint_class2b` 0 → 1 | `shard_f_membership.py` (shard F) |
| `lint_class2c` 60 → 61 | `344_pull_nigc_document_surface.py` (gaming) |
| `lint_class5` 6 → 7 | `shard_g_newsletters.py` (shard G) — `if uid in done:` |
| `tables_missing_codebook_block`, `tables_missing_from_25_TABLES`, `tables_missing_from_27_SPEC`, `tables_undocumented_in_codebook`, all +1..+5 | new tables in `data/clean/` from other workstreams. **Shard D writes nothing to `data/clean/`** — every output is under `data/staging/`, which `62` does not scan. |
| `F-DELAWARE-ALIAS` on `cedar_identifier_ledger_final.csv` / `_tiered.csv` | the identifier-ledger workstream |

### THE ONE WORTH READING — two shard programs, one lint class, opposite causes

Shard C, shard E, the lobbying workstream and I all tripped `lint_class4` on the
same day with the same line shape (`if <deadline/budget>: break`). That is not
four careless agents; it is **a defect class that every polite web puller
naturally writes**, because `PULL_DISCIPLINE.md` rule "BACKOFF BOUNDS THE RATE,
NOT THE RUN" *requires* a `RUN_DEADLINE`, and 293 correctly objects that a
deadline plus a success word with no coverage arithmetic is a silent truncation.

**The two rules are both right and they compose into one requirement nobody had
written down: a puller must have a deadline AND must publish, per run, what it
was asked for against what it got.** Any future shard probe should copy the
`expected_total` / `attempted_this_run` / `coverage_complete` block from
`code/553_shard_d_web_probe.py` rather than rediscovering this.

## GATE FAIL 2026-09-01 ~19:40 — NOT shard H. Owners named by the gate itself.

Recorded under standing rule 15 option 3 by **shard H** (the Native Hawaiian
Organization / state-recognized tribe / individually Native-owned business
slice: `data/staging/tribe_web_map/shard_h.csv`,
`data/staging/entity_profiles/shard_h.jsonl`,
`data/staging/anc_subsidiaries/shard_h.jsonl`,
`data/staging/tribe_harvest/shard_h/newsletters.jsonl`).

**The failing metrics, and `293`'s own attribution for the three lint lines:**

| line | moved | the instance `293` names |
|---|---|---|
| `lint_class2b` | 0 → 1 | `shard_f_membership.py` — **shard F** |
| `lint_class2c` | 60 → 61 | `344_pull_nigc_document_surface.py` — **gaming** |
| `lint_class5` | 6 → 7 | `shard_g_newsletters.py` — **shard G** |
| `lint_bug_class_instances` | 146 → 147 | the sum of the three above |
| `lint_new_defect_instances` | = 3 | the same three |
| `tables_missing_from_25_TABLES` | 179 → 184 | new `data/clean/` tables, below |
| `tables_missing_from_27_SPEC` | 194 → 195 | same |

**Proven not to be shard H.** This workstream wrote **no file in `code/`** — all
four of its scripts live in the session scratchpad
(`scratchpad/shardh/h1…h7`), which `293` does not scan and which cannot move a
lint metric. It created **no table in `data/clean/`**; its four outputs are in
`data/staging/`, outside every `ship_*` and `tables_missing_*` metric. Its only
`data/clean/` and `data/spine/` interaction is read-only.

The newest `data/clean/` arrivals by mtime, none of them shard H's:
`native_owned_businesses.csv` 19:26 (`code/330_build_native_owned_businesses.py`),
`nonprofit_schedule_c_lobbying.csv` / `nonprofit_schedule_c_coverage.csv` 19:20,
`regulations_gov_entity_coverage.csv` 19:15, `admin_appeal_positions.csv` 18:57.

This is the phenomenon the 2026-08-26 19:10 and 2026-09-01 16:45 entries above
already name — **a gate reading a shared tree mid-write, on a day with fourteen
live workstreams, reports another agent's incomplete step as a regression.**
Named, not shrugged at; the remedies belong to shards F and G and the gaming
workstream respectively.

---

## GATE FAIL 2026-09-01 ~20:1x — shard E. Two lines were mine; both fixed. Rest named.

Shard E (ANCSA corporate spiderweb) ran `62` at the end of its pass. **Exit 1.**
Per standing rule 15 this is recorded, not stepped around.

**Mine, and fixed in this pass** — both were flagged the moment they landed and
both are gone from the current `293` run:

| metric | line | what I did |
|---|---|---|
| `lint_class1` 0 → 2 then 0 → 4 | the `glob.glob` pairs in `531_shard_e_anc_report_mine.py` and `533_shard_e_build_subsidiary_edges.py` | **waived with a reason.** The interim text layer of the Alaska DBS STAR portal PDFs IS the source of record for this build; there is no promoted table of annual-report text and none is possible. The promoted artefact is the edge file `533` writes. |
| `lint_class4` | `if time.time() > RUN_DEADLINE:` in `532_shard_e_anc_web_probe.py` | **fixed, then waived.** The deadline no longer marks anything complete: every exit now writes `_coverage_<stage>.json` with `candidates_total`, `candidates_attempted`, an explicit `complete` boolean, `deadline_truncated`, and the unattempted URLs BY NAME; the host lock carries the same fields. This one mattered for real — a deadline-truncated crawl of a corporate tree must never be readable as the whole tree, because half a subsidiary list is a wrong answer, not a small one. |

`293` after the fixes names **no `*shard_e*` file in any class.**

**Not mine, named with their owners** — unchanged from the shard D and shard H
entries above, plus one that arrived after them:

| metric | new instance | owner |
|---|---|---|
| `lint_class2b` 0 → 1 | `shard_f_membership.py` | **shard F** |
| `lint_class2c` 60 → 61 | `344_pull_nigc_document_surface.py` | **gaming** |
| `lint_class5` 6 → 8 | `547_shard_c_hidden_endpoint_sweep.py`, `shard_g_newsletters.py` | **shards C and G** |
| `tables_missing_from_25_TABLES` / `_27_SPEC`, `native_owned_businesses.csv` at 0% ship | new `data/clean/` tables | `330_build_native_owned_businesses.py` and the other 19:1x–19:2x arrivals |

**Shard E adds no `data/clean/` table and no `data/spine/` write.** Its whole
output is under `data/staging/anc_subsidiaries/`, `data/staging/tribe_web_map/`
and `data/staging/tribe_harvest/shard_e/`, so it cannot move any `ship_*` or
`tables_missing_*` metric. Read-only against the spine, `503`, `510`, `512`.

*Also worth carrying forward from this pass, because it is a data-quality trap
and not a lint one:* the corroboration guard in `534_shard_e_build_web_map.py`.
A domain generated from an entity name that ANSWERS is not evidence it is the
right site — `englishbay.com` is a Vancouver photo blog, `nima.com` is somebody
else's business. A guessed URL is only recorded as the entity's site if the page
carries a distinctive token of the name AND an ANCSA/Alaska Native signal;
otherwise it is `UNRELATED_DOMAIN` with the reason. **A false "website found" is
worse than an honest absence**, and any shard generating candidate domains needs
the same check.

## A SOURCE'S OWN RETROSPECTIVE LABELLING IS NOT A FACT ABOUT THE PERIOD IT DESCRIBES (2026-09-01)

*Found by the owner, in one line: "1880? What data goes that far back lol."
Named here because it is a defect SHAPE this project had not written down, and
it will recur anywhere a modern publisher backfills a long series.*

The Osage Minerals Council publishes one spreadsheet titled **"OSAGE HEADRIGHT
HISTORY — 1880-2032 ACTUAL PRICES"**. Workstream O dropped a coverage floor to
the document's own floor and published all of it, applying the characterisation
the loop applied to every other Osage row:

```
commodity   = "Osage Mineral Estate (oil, gas, sand and gravel, water use)"
land_status = trust
confidence  = A on four rows
```

The Osage Mineral Estate was **created by the Osage Allotment Act of 1906**.
The first Osage oil lease of any kind was the **Foster lease, 1896-03-16**. So
sixteen rows asserted oil-and-gas revenue **from an estate that did not exist,
in years with no oil lease at all** — and the source itself says so, three
footnotes down: *"Individual payments began in 1909."*

**Nothing was fabricated.** Every figure is real, published, faithfully
transcribed; the 1906 quarters even passed the arithmetic gate. Every gate this
project has built — cross-foot, two-table agreement, verbatim-quote
verification — **passed, and none of them could have caught this**, because
they all check whether the NUMBER is right and this was a defect in what the
number was SAID TO BE.

### The shape

> A publisher extending a series backwards labels the whole series with its
> CURRENT vocabulary, because that is the only way to draw one continuous line.
> That labelling is a presentational convenience about the TABLE. Copying it
> into a typed field turns it into a historical claim about the PERIOD — one
> the publisher never made and the record may flatly contradict.

The tell is **a field value that needs a note to explain it does not mean what
it says.** The first version of these rows carried `land_status = trust` with a
basis reading *"the trust characterisation is stated for the estate as it
exists today, not as it stood in 1880."* That sentence is the bug reporting
itself. **A field that has to be annotated into meaning something else is a
wrong field value, not an annotated one.**

### What to do about it

1. **When you extend a series past a regime change, find the regime change and
   make the loop know about it.** Statutes, charters and programmes have start
   dates. `code/83_build_resource_ledger.py::_osage_period_fields` is the
   pattern: one function, both emission paths, three explicit regimes with the
   boundary years sourced in a comment block. Two inline conditionals would
   drift, and drift is how this happened.
2. **Blank beats confident-wrong, and `not_stated` beats `mixed`.** Where a
   published figure covers several mechanisms and no source apportions them,
   emit an empty commodity and `resource_type = not_stated`. Both are single
   cheap predicates a consumer can filter on. `mixed` is itself a claim — it
   asserts a mixture *of the things this column normally holds*.
3. **Do not substitute a plausible mechanism for a sourced one.** The prior
   here — trust interest on the Kansas land-sale proceeds — turned out to be
   the larger half of the right answer, and it would still have been wrong to
   write it into a field without a citation. It also missed grazing income,
   which *is* resource revenue, which is exactly the sort of thing a plausible
   inference misses.
4. **Confidence grades the ROW, not the arithmetic.** The four demoted rows
   passed their gate. A row whose commodity, resource type and land status are
   all unsupported for its own period is not tier-A evidence about anything,
   however good its sums.
5. **Ask what the series' own footnotes say before trusting its columns.** This
   sheet's third footnote — *"Individual payments began in 1909"* — was parsed,
   carried into the build, and printed to stdout, and nobody read it against
   the rows being written.

**And the cheapest check of all, which is what the owner actually did: look at
the earliest row and ask whether that thing existed yet.** A coverage mandate
makes floors drop, and a dropped floor walks a modern vocabulary backwards into
a period that never had it. Every long-series backfill should get that one
question before it ships.

Full write-up, sources and the resulting field-by-field decision:
`docs/datasets/natural_resources_sources.md`, "The pre-1907 classification
correction". The scoping question it raises is queued for the owner in
`review/OWNER_DECISION_QUEUE.md`.

### FOLLOW-UP 2026-09-01 — the brand-alias guard landed; the token bug did NOT

The lobbying workstream adopted shard J's brand-alias measurement into
`503_identity.py`'s `build_index` (104 single-token `alias_type='brand'` rows
refused; multi-token brand names kept, since "Ho-Chunk Inc" is a real trading
name). Confirmed live: `build_index` now prints the refusal and names the rows.

**The second defect is still open, and it is the more dangerous of the two.**
`503`'s loose-path guards (`ADMIN_GEOGRAPHY`, `CIVIC_FORM`) are denylists of
words, so they cannot refuse a civic form nobody has listed. Measured with
`py -3 code/541_shard_j_mine_990_mission_text.py --resolver-exposure`, which
calls `503.resolve()` READ-ONLY and writes only to `data/staging/np_mission/`:

    830  np_orgs organisations that 503 keys AND that have a local 990
    562  of them, the filing gives no Native word at all   <- a screen, not a verdict
     66  the filing states an affirmative NON-Native civic purpose, over 25 entities

`UMATILLA ELECTRIC COOPERATIVE ASSOCIATION` — the $592M leak named at the top
of `docs/datasets/06_nonprofit.md` — **still resolves to `TRBF-UMATLL-00`
today**, reason string *"gov-class distinctive-token match on 'Umatilla Tribe',
unique"*. So do Oneida-Madison Electric Cooperative, Oneida Healthcare Systems
(a 101-bed acute care hospital), Seneca Hose Co No 1, South Onondaga Fire
Department, Taos Volunteer Fire Department, the Puyallup, Washoe and Wyandotte
education associations, and 58 more.

The 562 are deliberately NOT claimed as errors: a tribal government's own 990
often says "services to our members" and names no Native word, so silence
proves nothing. Only the 66 carry an affirmative contradiction.

Evidence with quotes: `data/staging/np_mission/resolver_exposure.csv` (830
rows; `verdict = CONTRADICTED_BY_FILING` on the 66). Owner decision written up
as item **12e** in `review/OWNER_DECISION_QUEUE.md`, three options ranked.

**Owner of `503`:** the general fix is a shape rule, not more denylist words. A
distinctive-token set that is entirely a US settlement name is not distinctive
— *Fond du Lac* is two tokens and a Wisconsin city, so every organisation in
that city satisfies the subset test, and `ENVISION GREATER FOND DU LAC`,
`FOND DU LAC FESTIVALS INC` and `FOND DU LAC ADULT LITERACY SERVICES INC` prove
that no word list reaches them. The strongest available rule is that where
Cedar holds the organisation's own 990 and it states a non-Native purpose,
that evidence outranks any name match; the corpus is already on disk for 4,296
of the 12,764. Shard J did not touch `503`.

## GATE FAIL 2026-09-01 (late) — WORKSTREAM SHARD-C handing off. My two lines are cleared; the rest are named.

Shard C owns tribes 143–213 of the gaming slice. Two scripts were added:
`code/546_shard_c_tribe_web_probe.py` and
`code/547_shard_c_hidden_endpoint_sweep.py`. Everything else shard C wrote is
under `data/staging/`, which the gate does not scan.

### MINE, AND CLEARED IN THIS PASS

`lint_class5` — both instances are the SAME shape and both are now waived on the
line with a reason, per the gate's own instruction:

| line | why it is not the defect |
|---|---|
| `546_…probe.py:187` `if key in done` | the resume guard CARRIES the prior row forward unchanged, so a resumed run reproduces the earlier result and re-requests nothing |
| `547_…sweep.py:246` `if host in TERMS_RESTRICTIVE_HOSTS or (host, kind) in done` | `hidden_endpoints.jsonl` is append-only and `done` is rebuilt from it at startup; the TERMS half is a permanent, logged exclusion |

Class 5 is *"a non-idempotent build that rewrites its own log."* Both lines are
the opposite: remove them and the scripts become non-idempotent and re-hit every
tribal host on resume, which is exactly what `docs/PULL_DISCIPLINE.md` rule 6
exists to prevent. `293` counted `lint_class5` down 9 → 8 after the waivers.

`546` was also renamed from `shard_c_tribe_web_probe.py` to take a numeric prefix
above 545, as the naming convention expects. **546 and 547 are unique** — neither
is part of `code_duplicate_numbers`.

### NOT MINE — named, with owners

| line | owner | note |
|---|---|---|
| `code_duplicate_numbers` 43 → 44 | `561_shard_k_alaska_villages.py` / `561_shard_m_vendor_list_sweep.py` (on top of the pre-existing `561_pre2000_coverage_probe.py`) | three scripts now share 561. Two shards picked it concurrently; per the 2026-09-01 16:45 entry, whoever is still running keeps it and the later finisher moves. |
| `lint_class1` 0 → 1 | `570_shard_l_vendor_list_hunt.py:279` (shard L) | |
| `lint_class2b` 0 → 1 | `shard_f_membership.py:1` (shard F) | also has no numeric prefix |
| `lint_class2c` 60 → 61 | not attributable to a shard file by `293`'s listing; the 12 instances it names are all pre-existing `130`/`132`/`134` build scripts | the +1 is another workstream's; it is not in `546`/`547` |
| `lint_class5` remaining 6 → 8 | `570_shard_l_vendor_list_hunt.py:540` (shard L), `shard_g_newsletters.py:368` (shard G) | same resume-guard shape as mine; both are waivable on the line with a reason |
| `tables_missing_from_25_TABLES` 179 → 180, `tables_missing_from_27_SPEC` 194 → 195 | the new tables landing concurrently in `data/clean/` — `resource_parties.csv`, `resource_revenue.csv`, `native_owned_businesses.csv` (natural-resources and TERO-acquisition workstreams) | shard C created no table in `data/clean/`; every shard-C output is in `data/staging/`, which `62` does not scan |

Per the 2026-08-26 19:10 entry and the 2026-09-01 shard-launch entry: **a gate
reading a shared tree while fourteen workstreams write to it reports another
agent's in-flight step as a regression.** Named here rather than shrugged at, so
the next session does not re-diagnose them.

### ONE THING WORTH KEEPING — two name-matching domains that are NOT the tribe

`docs/NATIVE_ENTITY_NUANCES.md` says a place named for a tribe is not the tribe.
Two live examples turned up in shard C's slice, both of which a name-match
heuristic would have accepted:

* **`rockyboy.org`** — a Thai-language consumer-electronics blog.
* **`chippewacree.org`** — a link farm (`"Welcome to the family! - pbn"`).

Both would have been recorded as the Chippewa Cree Tribe of the Rocky Boy's
Reservation on a name match. The tribe's real host, `chippewacree-nsn.gov`, fails
at the transport layer, so **`TRBF-ROCKYB-00` is recorded with no government site
established** rather than with a plausible wrong one. That is the whole reason
`546` requires a token the page itself prints before it will call a site
established: a 200 is not evidence, and a matching domain name is not evidence.

### Shard H, re-run of the same gate at ~20:35 — the set moved, still none of it shard H's

The gate was re-run after shard H finished writing. Its failing set had changed
again in the intervening hour, which is itself the point: **five consecutive
runs of an unchanged gate produced five different regression sets**, because
fourteen workstreams are writing to one tree. `293`'s own attribution, verbatim:

```
NEW class1  instance: 570_shard_l_vendor_list_hunt.py  - glob.glob(... tribe_harvest ...)
NEW class2a instance: 570_shard_l_vendor_list_hunt.py  - row.setdefault("verdict", "")
NEW class2b instance: shard_f_membership.py            - shard_f_membership.py
NEW class5  instance: 570_shard_l_vendor_list_hunt.py  - if (host, kind) in done or not deadline_ok()
NEW class5  instance: shard_g_newsletters.py           - if uid in done:
```

Owners: **shard L** (`570_shard_l_vendor_list_hunt.py`, three of the five),
**shard F** (`shard_f_membership.py`), **shard G** (`shard_g_newsletters.py`).
`code_duplicate_numbers` 43 → 44 is a script-number collision between two of
the concurrently-launched shards, not a data defect — the rule from the 16:45
entry applies: whoever is still running keeps the number, the integrator moves.
`tables_missing_from_25_TABLES` / `_27_SPEC` are new `data/clean/` tables from
other workstreams.

Shard H's position is unchanged and re-verified: **zero files in `code/`**
(its scripts are session-scratchpad only, which `293` does not scan), **zero
tables in `data/clean/`**, four outputs all under `data/staging/`, and
read-only access to the spine. Its own product check passes:

```
py -3 -c "import csv,json; ... assert len(P)==319; assert no row claims federal recognition"
  -> shard_h ok 315 319 100 141
```


### Shard A, gate re-run ~19:5x — sixth different failing set, none of it shard A's

`62` fails, and every named new defect belongs to another concurrently-running
workstream. `293`'s own attribution across shard A's two runs of the gate:

```
NEW class2b instance: shard_f_membership.py                 - shard_f_membership.py
NEW class2c instance: 344_pull_nigc_document_surface.py     - skipped += 1
NEW class5  instance: 547_shard_c_hidden_endpoint_sweep.py  - if host in TERMS_RESTRICTIVE_HOSTS ...
NEW class5  instance: shard_g_newsletters.py                - if uid in done:
NEW class1/2a/5      : 570_shard_l_vendor_list_hunt.py      (three, per the shard H entry above)
```

Owners: **shard F** (`shard_f_membership.py`), **shard C**
(`547_shard_c_hidden_endpoint_sweep.py`, `344_pull_nigc_document_surface.py`),
**shard G** (`shard_g_newsletters.py`), **shard L**
(`570_shard_l_vendor_list_hunt.py`). `contract_violations` 6,
`contract_orphan_shippable` 5, `contract_grain_unstated_shippable` 25 -> 30 and
`code_duplicate_numbers` 43 -> 44 all track new `data/clean/` tables and new
`code/` scripts from other workstreams; shard A created neither.

Shard A's position: **zero files in `code/`** (all of its scripts are
session-scratchpad only, which `293` does not scan), **zero files in
`data/clean/`**, **no write to the spine**, and every output under
`data/staging/tribe_web_map/shard_a.csv` and `data/staging/tribe_harvest/shard_a/`
- neither of which `62` scans. Its own product check passes:

```
py -3 -c "import csv; R=list(csv.DictReader(open('data/staging/tribe_web_map/shard_a.csv',encoding='utf-8')));
          assert len({r['tribe_id'] for r in R})==71; print('shard_a ok', len(R))"
  -> shard_a ok 221
```

## GATE FAIL 2026-09-01 ~21:0x — grain workstreams. Owners named by the agents themselves.

GRAIN-WS2 verified each failing line individually and could not edit this file
(three agents were in `512` and several in `AGENTS.md`), so the attribution is
recorded here by the integrator on its behalf:

| line | owner |
|---|---|
| `lint_class7` +1 | `570_shard_l_vendor_list_hunt.py` (shard L) |
| `lint_class5` +1 | `571_shard_m_vendor_list_sweep.py` (shard M) |
| `code_duplicate_numbers` +1 | shards L and M both took **571** |
| `contract_grain_unstated_shippable` 25 → 29 | arithmetic: 5 new shippable tables registered by siblings, minus WS2's 1 declaration |

WS2 **improved** two metrics in the same pass: `contract_grain_stated_shippable`
185 → 186 and `harvest_source_rows_read` +49,694.

**Third number collision of the day** (532 twice, 547 twice, now 571 twice).
`ls code/<n>_*` is not sufficient when agents choose numbers concurrently. The
convention that has actually worked is a per-workstream floor assigned by the
integrator at launch, and even that failed when two shards were given the same
floor. Assign distinct floors.

### THE HUB IS NOT IN GIT (WS2, measured 2026-09-01)

`.gitignore:95` excludes `data/spine/*` except `cedar_identity_register.csv`
and `cedar_handle_history.csv`. **Git cannot restore `cedar_entity_spine.csv`.**

`01_build_entity_spine.py` fills the spine from `canonical_tribe_table.csv`
alone — 687 rows, 12 columns — against a live hub of **1,555 rows and 44
columns**. A direct invocation drops **868 entities (56%)**: 210 NHOs, 185 BIE
schools, 173 ANC village corporations, 64 Native CDFIs — and **32 of 44
columns, including `cedar_uid`**. `09_import_rulings.py` drops 1,345 ledger
rows, **18 of them tier A** (`elijah_ruling`, `nho_verified_entities`) — owner
adjudications, the one class of row that is not re-derivable.

Neither builder takes a `.bak`. All 15 spine enrichers do.

**Two things reduce the exposure.** `build.plan_for('_entity_layer')` already
sorts both into a `blocked` phase, so `build.py run _entity_layer --execute` —
the command 518 prints as the rebuild entry point — does not run them; the risk
is a direct invocation. And `handle` in the register equals `tribe_id` in the
spine for **all 1,555 rows**, so the uid binding survives inside a git-tracked
file. (`cedar_entity_id` covers only 1,009, so that route alone would have
recovered two thirds.)

**What is genuinely missing: a dependency-correct enricher replay order.**
`build.plan_for` returns them lexicographically (`50`, `503`, `51`, `52`…),
which is not the order they were applied, so nobody can prove a replay
reproduces 1,555 rows and 44 columns. Closing C8 needs exactly two changes:
`01`/`09` take a `.bak`, and the replay order is recorded and exercised once
against a census. Full write-up: `docs/WS2_GRAIN_AND_REBUILD.md` §5.

### `NAN` IS A CAGE CODE IN 2,196 ROWS

`fpds_uei_cage_map.csv` carries the **literal string `NAN`** — a stringified
null — in `cage_code` on 2,196 rows spanning **2,193 distinct UEIs**. A join on
`cage_code` that does not exclude it fuses 2,193 unrelated entities into one.

Excluding it, the route is near-exact: of 6,843 real CAGE codes only **15** map
to more than one UEI and none to more than two. That is the measured basis for
shard E's ASRC result, whose seven codes are all real.

### A TRIBAL GOVERNMENT IS NOT A NATURAL PERSON

`contractor_ranking.csv`'s privacy guard blanks identity columns on 134 rows,
and the withheld set includes **Nez Perce Tribe, Pueblo of Acoma, Rosebud Sioux
Tribe, Ramah Navajo Chapter, Blackfeet Utilities and Wyandotte Net Tel** — one
carrying $71.9M. The rule exists to protect natural persons and was never meant
to reach governments. It is also why the table has no validated key: all 19
non-measure columns still leave 6 duplicates, and **every collision is a
withheld row** (0 among the 1,295 published). Fix proposed by WS2: `269` emits
`operating_company_seq` (1..n within owner, existing sort order) — unique by
construction, leaks nothing.

### GATE FAIL 2026-09-01, second reading — SHARD-G's attribution

`62` exits 1 at 21:0x with 13 `!!` lines. **None of them is shard G's.** Shard G
added exactly two lint instances during its run and cleared both before this
reading, which is why neither appears below:

* `lint_class4` +1, `shard_g_registry_pull.py` — **FIXED, not waived.** The
  script now compares `result_count` against `expected_total` (the declared
  OBJECTS list) and sets `run_complete: false` with the missing keys named, so a
  deadline-truncated pull can never be read as a finished refresh. class4 is back
  at its baseline 9.
* `lint_class5` +1, `shard_g_newsletters.py` — **WAIVED with a reason in the
  source** (`# lint-ok: class5`). The resume guard is real, but the summary this
  file writes is recomputed by re-reading every record in `newsletters.jsonl`,
  prior runs included, so a resumed run reports the full standing totals rather
  than this run's zeros. That is the inverse of the class-5 defect. `293` counts
  and names the waiver.

The 13 lines that remain, with owners, measured 21:0x:

| line | owner named by the gate itself |
|---|---|
| `lint_class1` 0 → 2 | `573_ws3_grain_and_money.py` (`CLEAN.glob`), `585_factcheck_nigc_keys.py` |
| `lint_class5` 6 → 7 | `571_shard_m_vendor_list_sweep.py` (`if handle in existing`) |
| `lint_class7` 42 → 45 | `583_labor_surface_factcheck.py` (three: a RANK-derived `observation_id`, and two `id(r)` uses) |
| `lint_new_defect_instances` = 6, `lint_bug_class_instances` 146 → 150 | the same three files |
| `code_duplicate_numbers` 43 → 44 | a numbered script claimed concurrently. Shard G's four scripts are `shard_g_slice_and_mine.py`, `shard_g_registry_pull.py`, `shard_g_build_crosswalk.py`, `shard_g_web_map.py`, `shard_g_served_entity.py`, `shard_g_newsletters.py` — deliberately unnumbered, per concurrency rule 3, so they cannot collide |
| `tables_missing_from_25_TABLES` 179 → 186, `_27_SPEC` 194 → 201, `tables_undocumented_in_codebook` 3 → 10 | the 8 new `data/clean` tables the gate lists: `nigc_document_surface`, `native_owned_businesses`, `nigc_action_parties`, `nigc_enforcement_actions`, `sam_native_class_distributions`, `nigc_game_classification_opinions`, `nigc_indian_lands_opinions`, `nigc_management_contract_approvals` — gaming and SAM workstreams |
| `contract_violations` = 6, `contract_orphan_shippable` = 5 | same 8 new tables, no dataset contract yet |
| `F-DELAWARE-ALIAS` in `cedar_identifier_ledger_final/_tiered` | the correction register's owner; not touched today by shard G |

**Shard G writes nothing to `data/clean`, nothing to the spine and no numbered
script**, so it cannot move any of those lines. Its outputs are
`data/staging/institution_registry/`, `data/staging/tribe_harvest/shard_g/` and
`data/staging/tribe_web_map/shard_g.csv`, none of which `62` scans.

### Shard H, third run of the same gate at ~21:15 — sixth distinct failing set today

Re-run after shard H's identifier and adjudication pass. The set has changed
completely again; the shard L / shard F / shard G lint instances named an hour
ago have CLEARED, and `code_duplicate_numbers` is back to 43. What is failing now:

```
contract_orphan_shippable = 6            contract_violations = 8
contract_grain_unstated_shippable 25->32 files_with_columns_lost_vs_backup = 3
lint_class1 0->1  : 585_factcheck_nigc_keys.py   (gaming / fact-check)
lint_class6 +1    : 518_dataset_readiness.py     (dataset-standard workstream)
tables_missing_from_25_TABLES 179->185, _27_SPEC 194->200
SHIPPING LOST: advocacy_passthrough_2026-08-07.csv
```

The `SHIPPING LOST` line is a **read artifact, not a loss**:
`data/clean/advocacy_passthrough_2026-08-07.csv` is present on disk, 2,012,716
bytes, mtime Aug 28 23:43. The gate read the tree while another workstream was
mid-write. Anyone acting on that line should confirm the file first.

**Six consecutive runs of an unchanged gate, six different regression sets, none
of them shard H's.** Shard H has now written six files, every one under
`data/staging/`; `ls data/clean/*shard_h*` returns nothing and it has never held
a write handle on `data/clean`, `data/spine`, or `code/`. Its own product check
passes at every run:

```
shard_h ok  316 web-map rows | 319 profiles | 100 subsidiary edges
            141 newsletter rows | 70 identifiers | 10 class rulings
```

The standing lesson from the 2026-08-26 19:10 entry is now measured six times in
one day: **on a parallel-workstream day, `62` cannot attribute a failure by
itself, and the only reliable attribution is `293`'s own named instance plus a
file mtime compared against the live workstreams.**

## GATE FAIL 2026-09-01 ~21:2x — shard M. One line WAS mine and is fixed; the rest named.

`py -3 code/62_no_regression_check.py` exit 1. Shard M owns only
`review/tribal_vendor_list_registry_2026-08-26.csv` (149 appended rows),
`data/staging/business_registry/TBD-M0*.jsonl` + `shard_m_business_identifiers.jsonl`,
`data/staging/tribe_harvest/shard_m/**`, and `code/690_shard_m_vendor_list_sweep.py`.
It wrote nothing to `data/clean`.

### MINE, AND FIXED IN THE SAME PASS

`code_duplicate_numbers` 43 → 44, and it took **three renames**, which is the
point worth recording:

| I claimed | collided with | when |
|---|---|---|
| `561_shard_m_…` | `561_shard_k_alaska_villages.py` | shard K, mid-flight |
| `571_shard_m_…` | `571_closure_native_owned_businesses.py` | appeared after I moved |
| `588_shard_m_…` | `588_promote_self_published_claims.py` | appeared after I moved again |
| `690_shard_m_vendor_list_sweep.py` | — | free, and far from the active band |

`ls code/<n>_*` is not sufficient when a dozen agents are choosing numbers in
the same ten minutes — the check is stale the moment it returns. Two of these
three collisions were with scripts created *after* my check passed. **When many
agents are live, do not take the next free number in the active band; take one
several hundred above it.** `code_duplicate_numbers` is back to its 43 floor.

Also mine and fixed: `lint_class5` 6 → 7, `690_shard_m_…:if handle in existing`.
Waived with a reason rather than removed — the registry is append-only and
shard L is writing it concurrently, so that line stops a duplicate row; it
rewrites nothing and discards no prior result.

### NOT MINE — named, with owners

| line | owner |
|---|---|
| `lint_class1` 0 → 1, `585_factcheck_nigc_keys.py` (`FILES = [...staged.csv]`) | the NIGC / gaming workstream |
| `lint_class6` new instance, `518_dataset_readiness.py` → `cedar_dataset_readiness.csv` | owner of 518 |
| `files_with_columns_lost_vs_backup` = 3: `ca_gaming_facilities_official.csv` (−`entity_tier_basis`, `entity_keyed_date`), `entity_evidence_profile.csv` (−`in_spine`, `rows_per_source`, `amounts_per_source_NEVER_SUM`), `gaming_property_coverage.csv` (−`cedar_uid`) | gaming workstream and 505 |
| `contract_orphan_shippable` = 6, `contract_violations` = 8, `contract_grain_unstated_shippable` 25 → 32 | the contracts workstream |
| `corrections_not_propagated` 2 → 3 (BURNST casino host; DELAWARE alias in both identifier ledgers) | correction-register owner |
| `tables_missing_from_25_TABLES` 179 → 187 and `_27_SPEC` 194 → 202 | the eight new tables written to `data/clean` between 20:51 and 21:17 |
| `SHIPPING LOST: advocacy_passthrough_2026-08-07.csv` (1,620 rows, table gone) | advocacy workstream |

### THE ONE WORTH READING — an exclusion recorded in one mode did not bind another

Shard M read `www.stillaguamish.com/terms-of-use` **before** enumerating
anything, found *"prior written permission … Any unauthorized use of the
materials appearing on this site may violate copyright"*, and correctly dropped
the host. Four hours later its own `--deep` mode re-probed the same host and
pulled 1,506 media-index entries, because that mode's exclusion check consulted
only the hard-coded `TERMS_RESTRICTIVE_HOSTS` constant and never looked at the
verdict this same script had already written to its own log.

Quarantined to
`data/staging/tribe_harvest/shard_m/QUARANTINE_terms_restrictive_stillaguamish.jsonl`,
dropped from `deep_probe.jsonl` and `deep_hits.csv`, `publishable=N`, nothing
harvested. The fix is a `_restrictive_from_log()` lookup, but the generalisable
shape is:

> **A refusal recorded in one code path must be enforced from a single place
> every other path reads.** A constant plus a runtime verdict is two sources of
> truth for one decision, and the second mode written will consult the wrong
> one. Terms exclusions in particular get added over time — which is exactly
> when a hard-coded list goes stale.

The mirror-image defect, also shard M's, also worth one line: the terms matcher
fired on inline CSS in `nhbp-nsn.gov/legal/` and recorded Nottawaseppi
Potawatomi as TERMS_STATED_RESTRICTIVE. That page is the Legal *Department's*
page and states no restriction. **A false restrictive is not the safe direction
— it silently deletes a tribe from the study.** Strip tags and style blocks
before matching, and re-read every hit before recording it.

*Shard H addendum, ~21:30, fourth run:* same set reproduced, same owners
(`585_factcheck_nigc_keys.py`, `518_dataset_readiness.py`), plus one new line —
`corrections_not_propagated` 2 → 3, which belongs to the correction-register
workstream (`354_correction_register.py`), not to shard H. Shard H's file count
in `data/clean/` is still zero. Shard H is done; its two handoffs are
**HAND-638038475C** and **HAND-593FBD19BB**, both awaiting a different session
to verify.


---

## 2026-09-01 — `62` FAILS, and none of it is shard-I's

*Recorded under standing rule 15, which forbids writing "pre-existing, not mine"
and walking on. Shard-I (Native nonprofit harvest) ran `62_no_regression_check.py`
at the end of its run. **EXIT 1.** Shard-I owns `data/staging/np_harvest/` and
one appended section in `review/OWNER_DECISION_QUEUE.md`, and wrote nothing to
`code/`, `data/clean/`, `data/spine/` or `np_orgs.csv` — verified by
`git status`, and by `np_harvest` appearing **0 times** in the gate output.
`293_lint_bug_classes.py` scans `CODE = CEDAR / "code"` only, so this shard's
scripts are not even in its surface.*

**The failing lines and who owns them.** Each is a live concurrent workstream;
these are theirs to clear before their handoff:

| failing metric | named instance | owner |
|---|---|---|
| `lint_class1` 0 → 1 | `585_factcheck_nigc_keys.py` — `FILES = [...]` | NIGC fact-check workstream |
| `lint_class6` | `518_dataset_readiness.py` — `cedar_dataset_readiness.csv` | readiness workstream |
| `lint_class7` | `570_shard_l_vendor_list_hunt.py` — `f"{source_id}:{i}"` | shard L |
| `lint_class2c` 60 → 62 | `344_pull_nigc_document_surface.py`, `541_shard_j_mine_990_mission_text.py` | NIGC pull; **shard J** |
| `lint_class4` 9 → 10 | `shard_g_registry_pull.py` — `if time.time() > RUN_DEADLINE:` | shard G |
| `lint_class5` 6 → 7 | `221_probe_regulations_gov_comments.py` | regulations.gov workstream |
| `files_with_columns_lost_vs_backup` = 3 | `ca_gaming_facilities_official.csv`, `entity_evidence_profile.csv`, `gaming_property_coverage.csv` | gaming / evidence-profile workstreams |
| `contract_violations` = 8, `contract_orphan_shippable` = 6 | — | contracts workstream |
| `corrections_not_propagated` 2 → 3 | `TRBF-BURNST-00`→`oldcampcasino.com`; `TRBF-DELAWN-00`→`Delaware Tribe of Indians` | gaming property; identifier ledger |
| `SHIPPING LOST` | `advocacy_passthrough_2026-08-07.csv` gone from `data/clean` | advocacy workstream |

**One of these is worth a second look by whoever integrates.** `SHIPPING LOST:
advocacy_passthrough_2026-08-07.csv was shipping 1,620 rows and the table is
GONE from data/clean`. A vanished shipping table is a different shape of defect
from a lint rise: the others are new code that can be fixed in place, this one
is data that is no longer there. It is the same class the 144 `cedar_uid` note
above describes — a rebuild writer dropping what it did not know about.

**Shard-I's own gate state, for the record:** the shard produced no table in
`data/clean`, no `code/` module, and no contract-covered output, so there is no
metric in `62` it could move in either direction. Its outputs are staging
artefacts and a review proposal, both of which are outside the gate's surface by
design — nothing here is a waiver.

## `advocacy_passthrough_2026-08-07.csv` IS NOT LOST — THAT LINE IS MINE

Three separate agents have now stopped to investigate `62`'s
`SHIPPING LOST: advocacy_passthrough_2026-08-07.csv ... GONE from data/clean`,
and two correctly diagnosed it as a mid-write artifact. It is neither lost nor
an artifact. **It is a deliberate change I made on 2026-09-01, and the gate's
wording is wrong.**

The file is on disk at 2,012,716 bytes and reads 1,620 rows. What changed is
its shipping status: it and `advocacy_passthrough.csv` were **both**
`status=shippable` in the lobbying collection, 1,620 rows each, the same
$193,592,975 in `grant_amount_usd` — so anyone totalling the collection's
pass-through got $387M. The dated snapshot is now `internal-by-decision` via
`cedar_codebook`, following the precedent already in that file for
`cedar_identifier_ledger_tiered.csv`.

So the metric moved for the right reason and the message is misleading: a table
leaving the ship list reports as **GONE from `data/clean`**, which sends a
reader to look for a missing file. **Nobody should spend further time on it.**

The gate line deserves fixing to distinguish *deregistered* from *deleted* —
they are opposite situations and only one is an incident. Recorded here rather
than fixed, because `62` is the shared gate and several agents are live.

## THE 990-N e-POSTCARD CORPUS IS NOW IN `data/raw/external/irs990n/`

Shard I found it and asked for it to be promoted out of its staging directory.
Done, with a manifest. It is the **only public source carrying a website field
for 990-N postcard filers**, and it is one 93 MB object rather than thousands of
per-organisation fetches — 86.4% of Cedar's `990_N` stratum appears in it and
20.6% carry a non-blank website field.

It is also the measurement that closes a question: **do not run a further web
sweep on the remaining 6,353 postcard filers.** Shard I measured the whole
population rather than sampling, and the funnel collapses about 100:1 —
1,476 website fields, 1,019 parse as a URL, 864 answer 2xx, 251 carry an
evidence-bearing sentence, **15 assert Native control**. For
`not_required_to_file` the field rate is 0.83%, and 1,491 of those 2,060 are
churches. The cheap routes left are state charity registries and
group-exemption parents, which are bounded objects rather than per-org fetches.


## GATE FAIL 2026-09-01 — shard L. Nothing red is mine; every line named with its owner.

`py -3 code/62_no_regression_check.py` exit 1. Shard L owns only
`review/tribal_vendor_list_registry_2026-08-26.csv` (148 appended rows; the
149th tribe in its slice, `TRBF-MNACAN-00`, was already present because shard M
took the split boundary, and shard L skipped it rather than duplicate it),
`data/staging/business_registry/TBD-L0*.jsonl` + `TBD-L1*.jsonl` +
`TBD-L00_business_identifiers*.jsonl`, `data/staging/tribe_harvest/shard_l/**`,
and `code/570_shard_l_vendor_list_hunt.py`. **It wrote nothing to `data/clean`.**

### Every metric shard L could move is at or under its floor

| metric | value | floor |
|---|---:|---:|
| `code_duplicate_numbers` | 43 | 43 — `570_` is unique; checked against `code/` after shard M's three collisions |
| `lint_class1` | 0 | 0 — shard L's one instance is waived with a reason at `570_…:311` |
| `lint_class5` | 6 | 6 — waived at `570_…:692` |
| `lint_class7` | 42 | 42 — waived at the `business_source_id` line |
| `lint_bug_class_instances` | 144 | fell 146 → 144 |

### RED, AND NAMED WITH ITS OWNER

| line | owner |
|---|---|
| `lint_new_defect_instances = 1` — `NEW class6 instance: 518_dataset_readiness.py - cedar_dataset_readiness.csv` | 518's author; a full-rebuild/in-place-enricher ordering, not a shard-L file |
| `files_with_columns_lost_vs_backup = 1` — `entity_evidence_profile.csv` 10 → 9 cols vs `.bak_2026-08-28_pre505`, lost `in_spine`, `rows_per_source`, `amounts_per_source_NEVER_SUM` | whoever ran 505 / the profile rebuild; shard L never opened this table |
| `contract_violations = 8`, `contract_orphan_shippable = 6`, `contract_grain_unstated_shippable` 25 → 32 | the same 8 new `data/clean` tables named in the shard G entry above; shard L added no table |
| `tables_missing_from_25_TABLES` 179 → 187, `tables_missing_from_27_SPEC` 194 → 202 | ditto — new `data/clean` tables not yet in the curated override lists |
| `SHIPPING LOST: advocacy_passthrough_2026-08-07.csv` (1,620 rows, gone from `data/clean`) | the advocacy-passthrough rebuild; shard L does not touch `data/clean` |

Recorded rather than stepped around, per standing rule 15.

### One finding worth keeping, from the same pass

Shard M's `--deep` breach — an exclusion enforced in one branch and not another
— was checked for in `570` and the two branches were **merged into one**.
`_blocked_hosts()` is now the single source of truth: it unions the named
`TERMS_STATED_RESTRICTIVE` hosts with every host whose own terms page this run
recorded as restrictive, and it is read by `get()`, which is the one chokepoint
every request in the script passes through. `TERMS_RESTRICTIVE_HOSTS` is
referenced in exactly one place — inside `_blocked_hosts()`. A refusal that only
some code paths honour is not a refusal.

## MTIME ANSWERS FRESHNESS. IT SAYS NOTHING ABOUT COMPLETENESS.

*Measured 2026-09-01 on `native_passthrough.csv`.*

An earlier pass concluded that table was stale because `subawards.csv` had
grown. A later pass concluded it was current because **both files carry the
identical mtime, `08-29 01:32`.** Both readings were wrong, and the second was
wrong in the more dangerous direction.

The direct test:

```
subawards.csv primary rows                       55,316
  both prime AND sub are Native                     952   distinct subaward_number
    present in native_passthrough                   759
    MISSING                                         193   = 20%
passthrough keys orphaned (not in subawards)          0
```

**Zero orphans and 193 missing.** The projection is not pointing at rows that
have gone; it never saw rows that arrived. A timestamp cannot distinguish those
because both files were written in the same run — the builder simply read a
`subawards.csv` that was still growing.

And it is not a filter: the missing rows spread across **every** tier pair —
A/A 34, A/B 24, B/A 85, B/B 71. A confidence rule would leave one pair complete
and the rest absent.

### The general rule

> **Freshness is "was this rebuilt after its input changed" and mtime answers
> it. Completeness is "does the output cover everything the input now
> supports", and only a re-derivation answers that.**

A derived table can be perfectly fresh and 20% incomplete. Test a projection by
re-deriving its candidate set from the current source and diffing both ways:

- **candidates missing from the output** → incomplete (this case)
- **output keys absent from the source** → orphaned by a source change

Neither shows up in a timestamp, a row count, or an interior-gap check. The
docs workstream hit the same wall from the other side today: `subawards`
FY2022–24 hold 89/120/166 rows against neighbours of 9,462 and 7,360, and
`35_coverage_audit.py` correctly reports **no gap**, because those years are
non-zero. That is why `621` now flags **thin** years at under 20% of a table's
median — a different instrument for a defect a gap check structurally cannot
see.

**Build order follows from this.** Declare a grain or validate a key only
against a table that is not about to change. A key validated against a table
that then gains 193 rows was validated against the wrong table.

## GATE ATTRIBUTION 2026-09-01 ~22:0x — three lines the cadence workstream could not record

It is not permitted to edit this file, so the integrator records its findings:

- `lint_new_defect_instances = 2` → **`518_dataset_readiness.py`** and
  **`73_faads_name_attribution.py`**, both class6, named by the gate itself.
  The 518 instance is mine, from adding the OWNERS check.
- `files_with_columns_lost_vs_backup = 1` → **`entity_evidence_profile.csv`**,
  10 → 9 columns against `.bak_2026-08-28_pre505`, losing `in_spine`,
  `rows_per_source` and `amounts_per_source_NEVER_SUM`. That last name is doing
  work — a column literally called NEVER_SUM disappearing is the kind of loss
  that turns into a double count downstream.
- `SHIPPING LOST: advocacy_passthrough_2026-08-07.csv` → **already explained
  above and still not a loss.** Fourth workstream to stop on it. The file is on
  disk at 2,012,716 bytes; it left the shipping set because I deregistered it.

## GAMING GRAIN ROUTED, AND THE ROUTING WAS THE BLOCKER

INT-2 promoted six NIGC tables into `data/clean` and `dist/cedar_press.db`, and
gaming's C1 count went **1 → 7**. Not because the work was bad — because grain
lives in `512`, GRAIN-WS3 owned gaming's block, and WS3 had finished. Six
freshly promoted tables sat UNSTATED with their declarations written out in
`review/GRAIN_WS3_REQUEST_gaming_nigc_2026-09-01.md` and nowhere to put them.

**Acquisition moved the scoreboard backwards because nobody could route a
declaration.** Routed as `GRAIN_GAMING` in 512; gaming is now **UNSTATED on 3**.

The generalisable point: a per-workstream block solves the concurrent-edit
collision and creates an orphaning problem when a workstream ends. **When a
workstream finishes, its block needs an heir** — otherwise the next agent to
touch that dataset has measured declarations and no legal place to write them.

---

# WORKSTREAM INT-READY, 2026-09-02 — the five READY datasets, and the gate lines that are not ours

Scope: promote what `docs/WHAT_IS_MISSING.md` found ON_DISK_NOT_PROMOTED in
`gaming`, `lobbying`, `federal-register`, `nagpra` and `_entity_layer`. New
scripts **960, 961, 962** (the 960–979 band). All five datasets are still
READY; `lobbying` went 33 → 35 shippable tables.

## Standing rule 15 — naming the gate lines, and whose they are

`62_no_regression_check.py` fails. **One line was ours and is fixed; the rest
are named here with their owner so the next workstream does not step around
them a seventh time.**

| line | ours? | who |
|---|---|---|
| `lint_class7` NEW: `962…probe_id=f"FR-TERM-{i}"` | **YES — FIXED** | a loop index as a key. Now `stable_digest((host, phrase))`. 293 confirms the instance is gone. |
| `lint_class1` NEW ×1 | no | `1011_cross_dataset_reconciliation.py` — **`glob("deals_*_additions.csv")`, the exact additions-only glob that miscounted deals as 790 and is repaired at source in 88 and 57.** Third time this pattern has been re-typed. |
| `lint_class2c` NEW ×4 | no | `1060_splink_pilot.py` (×2), `852_extend_constellation_edges.py`, `873_build_aiannh_crosswalk.py` |
| `lint_class3` NEW ×2 | no | `1060_splink_pilot.py`, `992_newsletter_deal_candidates.py` |
| `lint_class4` NEW ×2 | no | `1031_ancsa_45_55_139_annual_reports.py`, `992_newsletter_deal_candidates.py` |
| `lint_class6` NEW ×3 | no | `518_dataset_readiness.py`, `870_build_geo_crosswalks.py`, `871_promote_geo_keys_contracts.py` |
| `files_with_columns_lost_vs_backup` (2 on the first run, **1** on the second) | no | `entity_evidence_profile.csv` (505, already named above in this file) and `federal_funding_tribe_year_panel.csv` (`tribe_id`, `tribe_id_scheme` against `.bak_2026-09-01_pre843`) — the second was repaired between our two gate runs. **Neither of our two enriched tables lost a column**; both gained only. |
| `tables_undocumented_in_codebook 3 → 17` | no | the 14 named in the gate output are `geo_*` (870/871), `cedar_constellation_*` (851/852), `tribal_newsletter_*` (992), `native_business_*`, `cedar_entity_freshness.csv` (830). Our one new table, `consultation_source_probe.csv`, is registered in `cedar_codebook.INTERNAL_TABLES` and is not in that list. |
| `contract_orphan_shippable = 7` | **partly ours, downward** | we REMOVED two (`nonprofit_schedule_c_lobbying.csv`, `nonprofit_schedule_c_coverage.csv`) by claiming them for `lobbying` in `500.COLLECTIONS` and declaring their grain in `512.GRAIN_INT_READY`. The seven that remain are two `native_owned_businesses.bak_*.csv` and one `prime_contracts.bak_*.csv` **registered in the codebook as if they were tables** — that is a bug in whatever registered a `.bak` file — plus `native_owned_businesses.csv`, `regulations_gov_comments.csv`, `regulations_gov_entity_coverage.csv` (live harvest by `221`, pid 1556 at the time of writing — left alone deliberately) and `sam_native_class_distributions.csv`. |
| `SHIPPING LOST: advocacy_passthrough_2026-08-07.csv` | no | **fifth workstream to stop on it.** Still on disk. Already explained above. |

## Two enrichers declared in `cedar_pipeline.KNOWN_ORDERINGS`

`23d_build_gaming_facilities.py → 960` (11 columns) and
`503_identity.py → 961` (5 columns). Both "not yet paid".

**And 503 carries a live landmine, recorded as `docs/KNOWN_ISSUES.md` D1:** its
`regcols` list at line 1090 still names `same_as_legacy_cicd`, which `843`
retired from the data on 2026-09-01. A 503 rebuild reintroduces a retired
identifier scheme as an empty named column. Not fixed here — 503 is
identity-critical and owned elsewhere — but it is a one-line change and someone
who owns it should make it.

## The lesson worth keeping: a guessed 404 is not a probe

`docs/WHAT_IS_MISSING.md` said DOI posts *"dozens a year"* of Dear Tribal
Leader letters against Cedar's 6, and its own Method section called that the
weakest claim in the document. 962's first draft "probed" it by trying three
guessed URL paths on bia.gov, collecting three 404s, and was about to record
`NOT_IN_SOURCE` — **concluding from three guesses that a publisher does not
publish**, which is the exact inversion of the rule in
`docs/HIDDEN_DATA_TECHNIQUES.md`. The rewrite asks the publisher's own
enumeration (`sitemap.xml`) instead, and the answer changed:

- The **Federal Register itself** holds **46** documents containing the phrase,
  **14** of them Interior's. Cedar's 6 is a thin reading of a source whose
  ceiling is 46 — not evidence of a broken parser, and not "dozens a year".
- **bia.gov enumerates 10 Dear Tribal Leader letters in its own sitemap**
  (2,412 URLs), outside the Federal Register, under robots-allowed `/news/`.
  A **FLOOR**, because a paginated Drupal sitemap need not carry every node.
- **ihs.gov answered HTTP 406** and is recorded `NOT_CHECKED`, never as an
  absence.

So both halves of the original inference were half right, and neither could
have been settled by counting rows.

## GATE STATE AT THE CLOSE OF WORKSTREAM PROMOTE (2026-09-02) — named, not stepped around

Standing rule 15 says a red gate is stop-work and that a failure belonging to
another agent must be **named with its owner** before moving on. This is that
naming. `py -3 code/62_no_regression_check.py` exits 1; the log is
`logs/promote_62.log`.

**Nothing red is workstream PROMOTE's.** Evidence, not assertion:

- `py -3 code/293_lint_bug_classes.py` names **12 new instances and not one is
  a `95x` script**. One was — `class2c 950_promote_contract_attributes.py:
  orphan += 1`, a counter that did not name what it found — and it was fixed
  (the orphan and malformed-NAICS counters now carry the offending
  `contract_number` / `fiscal_year` / value). `grep -E '95[0-9]_'` over the
  full lint report returns nothing.
- `files_with_columns_lost_vs_backup` names `entity_evidence_profile.csv`
  (`in_spine`, `rows_per_source`, `amounts_per_source_NEVER_SUM` lost vs
  `.bak_2026-08-28_pre505`) and, earlier in the same session,
  `federal_funding_tribe_year_panel.csv`. Neither is a PROMOTE table.
- All three PROMOTE tables re-verify green **after** other agents wrote to
  them: `950/952/953 verify` all exit 0, and 950's INV-COPY re-reads all
  841,002 archive rows.

**Named, with owners, in the order a reader will meet them in the log:**

| red line | owner, by evidence |
|---|---|
| `lint_class1` 0→1 | `1011_cross_dataset_reconciliation.py` — globs `deals_*_additions.csv` |
| `lint_class2c` 60→65 | `852_extend_constellation_edges.py`, `873_build_aiannh_crosswalk.py` and two later arrivals |
| `lint_class3` 0→2 | `992_newsletter_deal_candidates.py` — `deal_status_std == "Closed"` read as a ruling |
| `lint_class4` 9→11 | `1030_sec_edgar_native_transactions.py`, `1031_ancsa_45_55_139_annual_reports.py`, `992_*` — `RUN_DEADLINE_S` |
| `lint_class7` 42→46 | `1030_*` (`SEC1030-{n:06d}`) and `1031_*` (`AS4555139-{n:05d}`) — positional ids |
| `class6` (not itself red) | `871_promote_geo_keys_contracts.py` enriches `prime_contracts.csv` in place with **no declared ordering**. 950 does the same and is NOT flagged, because its `40 → 950` ordering is in `cedar_pipeline.KNOWN_ORDERINGS`. The fix for 871 is one entry in the same list. |
| `contract_orphan_shippable = 7` | see the two sub-items below |
| `tables_*` / `ship_tables_at_zero` all rising together | new tables landed in `data/clean` from several workstreams faster than `25_build_publication_layer.TABLES` and the codebook registry were updated. Not one table; a registry lag. |
| `rulings_unapplied` 1,215→2,894 | a rulings-side workstream; no PROMOTE script reads or writes a ruling |
| `SHIPPING LOST: advocacy_passthrough_2026-08-07.csv`; `hearing_bill_links.csv` 465→464; `native_bills_subject_sweep.csv` 2,414→2,409 | the advocacy and legislation workstreams |

### Two of those seven orphans are a backup-naming breach, and one is a real defect

**1. Three files are backups wearing a table's name.**
`native_owned_businesses.bak_2026-09-02_010526.csv`,
`native_owned_businesses.bak_2026-09-02_010557.csv` and
`prime_contracts.bak_2026-09-02_011205_pre772.csv` are counted as ORPHAN
SHIPPABLE TABLES by `512_build_dataset_contracts.py` — because the convention
is `<file>.csv.bak_<date>_pre_<script>` and `.bak_` must fall AFTER the `.csv`,
which is what `build.py :: collection_tables` filters on. These three put it
before, so every scanner reads them as new tables in `data/clean`. Owner:
whoever ran `772_strip_nan_sentinels.py` and the two 01:05 native-owned-business
passes. **Renaming another agent's backup mid-pass is exactly what concurrency
rule 2 forbids, so they are named here and left alone.** Three of the seven
orphans disappear the moment they are renamed.

**2. `native_owned_businesses.csv` — the flagship table of a READY collection —
is claimed by NO collection.** Not a naming artefact. The `native-owned-
businesses` collection in `code/500_build_architecture_map.py` matches
`^(individual_native|tribal_certification)`, and `native_owned_businesses`
matches neither. So the actual product table has no collection, no rebuild
plan and no contract, while `518_dataset_readiness.py` reports the dataset
READY on its other six tables. The one-line fix is to widen that regex.

**It was NOT applied here, deliberately.** The collection's own comment block
scopes it to *"firms owned by PEOPLE, not nations"*, and
`575_closure_native_owned_businesses.py` is another workstream's closure pass
over the same dataset. Widening the regex changes what an entire collection
claims, which is that workstream's call and not a promotion pass's. **Owner:
whoever owns 575 / the `owned` product collection.**

---

## 2026-09-02 — workstream SUBAWARD-FUNDING: gate state on close, and two things another workstream owns

*Recorded per standing rule 15 option 3, which forbids writing "pre-existing,
not mine" and continuing. This workstream took `subcontracting` and `funding`
from BLOCKED to READY (`py -3 code/518_dataset_readiness.py` → **13/13 READY**).
`62_no_regression_check.py` exits 1 on close and NONE of its failing lines is
this workstream's. They are named below with their owners so the next reader
can trace rather than guess.*

### What this workstream changed

| file | what |
|---|---|
| `code/910_subaward_report_id_backfill.py` | new. Recovers `subaward_sam_report_id` from staged zips (8.48M raw rows, zero network) and derives `subaward_source_record_id`. `subawards.csv` gets its first primary key: **(source_dataset, subaward_source_record_id)**, 0 blank, 0 collisions. Byte-identical rows 10,770 → 0 with **zero rows deleted** and money identical to the cent |
| `code/911_subaward_sub_leg_cedar_uid.py` | new. `prime_cedar_uid` / `sub_cedar_uid`. C4 42% → 99.90%, because a subaward has two legs and only the prime one had an id |
| `code/912_selftest_refusal_gates.py` | new. Proves the three new gates fire on synthetic violations |
| `code/81_build_passthrough_dataset.py` | carries the parent's key + `duplicate_status` + `subaward_exceeds_prime_flag`; gained `verify`, a backup, and before/after conservation printing |
| `code/512_build_dataset_contracts.py` | new block `GRAIN_SUBAWARD_FUNDING` + four side maps + `_validate_refusal`. **Own block only; nothing else touched.** UNSTATED 10 → 7 |
| `code/517_export_safety.py` | fourth export class `AGGREGATE_ONLY_NO_KEY` |
| `code/518_dataset_readiness.py` | C2 accepts a re-measured key refusal; C3 implements its own "or intentionally explained"; C4 defect (5), the national-mirror denominator |
| `code/574_ws1_money_and_conservation.py` | "Why no primary key is declared" → "The keys — three of four declared, one REFUSED", measured from the live files |
| `code/121_pull_subawards_api.py` | new `POST_PROMOTION_COLS` map (see below) |
| `code/cedar_pipeline.py` | four `KNOWN_ORDERINGS` entries for subawards.csv / native_passthrough.csv |

### A LESSON WORTH MORE THAN THE FIX: a correction that lives only in a generated file has a deletion date on it

`docs/MONEY_TOTALLING_RULES.md` carried a hand-written paragraph — *"State the
denominator, every time"* — added after Codex found the subaward overstatement
quoted as **46.5%** in one shipped description and **86.9%** in another. The
paragraph was correct and it was written into the **output**. `574` writes that
file **wholesale**. The first re-run of 574 deleted it silently, and the
document went back to quoting one denominator with no warning attached.

It is now computed inside 574 from the same two totals as the sentence above
it, so it cannot be deleted by a rebuild and cannot drift from the numbers it
describes. **If you correct a generated document, correct the generator.**

### `62_no_regression_check.py` FAILS on close. None of it is mine.

Checked line by line against `293.new_since_baseline()`, whose finding key is
`class|file|evidence` and therefore immune to the line-number shifts my edits
caused:

* **`lint_new_defect_instances = 17`** — named files are `1011`, `1072`, `1060`,
  `852`, `873`, `992`, `1030`, `1031`, `980`, `870`, `871` and **`518`**. All
  but the last belong to the constellation, geography, newsletter, EDGAR,
  business-registry and splink workstreams. **The `518` one is a file this
  workstream edited, so it was checked rather than waved past**, and it is not
  ours: `class6|518_dataset_readiness.py|cedar_dataset_readiness.csv` fires
  because `621_dataset_coverage.py` both READS and WRITES that table while 518
  rebuilds it — a rebuild-vs-enricher pair. `621` was last changed in commit
  `c82e9bd` (the C4-scanner-v2 workstream) and `518` does not read the table at
  all; measured with `293.table_io` on both files. **Owner: whoever owns `621`
  — either 621 should stop writing it, or the pair needs a
  `cedar_pipeline.KNOWN_ORDERINGS` entry with 621 running LAST.** Every 518 run
  in this workstream was checked against the previous header and lost no
  column.
* **`files_with_columns_lost_vs_backup = 1`** — `entity_evidence_profile.csv`
  lost `in_spine`, `rows_per_source`, `amounts_per_source_NEVER_SUM` against
  its `pre505` backup. Owner: `151_rebuild_entity_evidence_profile.py` /
  `503_identity.py`.
* **`contract_violations = 12` and `contract_orphan_shippable = 7`** — both
  present at the same values before this workstream started (baseline snapshot
  taken at 2026-09-02 before the first edit) and unchanged by it. Five of the
  seven orphans are `.bak_*` files another workstream left in `data/clean/`.
* **`rulings_unapplied 1,215 → 2,894`**, **`tables_undocumented_in_codebook
  3 → 18`**, **`ship_tables_at_zero 13 → 17`**, the two "stopped shipping"
  lines (`hearing_bill_links.csv` 465→464, `native_bills_subject_sweep.csv`
  2,414→2,409, both the legislation workstream's deliberate corpus de-dupe) and
  `advocacy_passthrough_2026-08-07.csv` — none is reachable from any file this
  workstream touched.

Metrics this workstream **improved**: `contract_grain_stated_shippable`
185 → 218, `contract_grain_unstated_shippable` 25 → 7,
`export_unsafe_money_tables` **11 → 0**.

### GEOGRAPHY WORKSTREAM: `871` silently broke `121`, and I unblocked it on your behalf

`871_promote_geo_keys_contracts.py` added ten `geo_*` columns to
`subawards.csv` at 01:14 on 2026-09-02. `121_pull_subawards_api.py` has a
schema guard that **raises SystemExit** on any column beyond the promoted
schema that `append()` cannot fill, and all ten qualified — so the FY2022–24
subaward promotion that is mid-flight **could not run at all**, and the failure
would have read as a schema problem with the pull rather than as a column
addition somewhere else.

Registered in the new `POST_PROMOTION_COLS` map in 121 and in
`cedar_pipeline.KNOWN_ORDERINGS`, on the reasoning that 871 is an in-place
enricher keyed on `prime_award_unique_key` — a column every row already carries
— so it recomputes cleanly for appended rows and must simply RUN AFTER the
promotion. **Geography workstream: if that is wrong, the line to correct is
named in 121's comment.**

The full post-promotion order is now printed by the guard itself and registered
in `cedar_pipeline`: `910 rescan → 910 apply → 911 apply → 871 → 81`.

### The three new ways to satisfy the contract, and why each has its own gate

A hole in a gate is only safe if the hole has its own gate — *"a check reading a
key that does not exist passes for the same reason it is useless."*

| the hole | the gate on the hole | proof it fires |
|---|---|---|
| a declared key **REFUSAL** substitutes for a primary key | `512._validate_refusal` re-measures every refused candidate on the FULL file each run; a candidate that has become unique is a **violation** — *a key we could publish and do not is a defect* | `912` T1 |
| a declared **duplicate disposition** substitutes for removing duplicates | the disposition states an exact expected count; any drift, in either direction, breaks the declaration | `912` T2 |
| a declared **`national_mirror`** scope leaves C4's denominator | the claim must name the table holding the Native attribution; that table must exist and be ≥50% attached, or the claim is refused and the mirror is scored as before | `912` T4 |

Each has a matching control (C1–C4) proving it does not over-fire.

---

## GATE ATTRIBUTION 2026-09-02 — workstream `nest` (dataset 14)

`code/1072_tribally_owned_enterprises.py` built **NEST: Native Enterprise
Structures and Ties** — `data/clean/nest_enterprises.csv` (1,482) and
`nest_enterprise_relations.csv` (3,492). `518` reports **READY 14 / 14**. Full
record in **`docs/NEST_BUILD_LOG.md`**.

**`62_no_regression_check.py` exits 1.** Naming what is and is not this
workstream's, with the measurement, per standing rule 15.

**NOT ours — checked, not asserted:**

- `lint_bug_class_instances`, `lint_class1/2c/3/4/5/7`. **`293` reports ZERO
  findings in `1072_*` across all seven classes.** The new-since-baseline list
  names `1011`, `1060`, `846`, `852`, `873`, `992`, `1030`, `1031`, `980`,
  `1075`, `1077`, `845`, `870`, `871`, `518`, `77`. One class-1 finding *was*
  raised against 1072 and was **fixed, not waived**: the business-registry loop
  globbed `TBD-*.jsonl`, a prefix filter with the same shape as the deals
  additions glob that omitted 131 rows. It now enumerates `*.jsonl` and selects
  on the row (`directory_type = subsidiary_directory`), and `1072` is declared
  in `cedar_domain.PROMOTED_TABLE_PRODUCERS` because reading the staged parts
  is its job and it reads every one.
- `contract_violations = 11`. The 11 are four `federal_funding_*` declarations
  naming the dropped `tribe_id` column and seven orphan shippable tables
  (`native_owned_businesses*`, `prime_contracts.bak_*`, `regulations_gov_*`,
  `sam_native_class_distributions`). **NEST contributed 2 and they are fixed** —
  both tables now carry `cedar_uid`, which is the documented external join key
  and which the declaration had promised before the column existed.
- `rulings_unapplied 1,215 → 2,894`, `files_with_columns_lost_vs_backup = 4`,
  `SHIPPING LOST: advocacy_passthrough_2026-08-07.csv`, and the two tables that
  stopped shipping (`hearing_bill_links`, `native_bills_subject_sweep`). This
  workstream wrote none of those files.

**OURS, and open:**

- **`nest_enterprises.csv` and `nest_enterprise_relations.csv` are BUILT and
  DOCUMENTED but NOT SHIPPED.** They are 2 of the ~20 tables behind
  `tables_missing_from_25_TABLES`, `tables_missing_notes_contract`,
  `ship_tables_at_zero` and `tables_undocumented_in_codebook`; the other ~18 are
  the geography workstream's `geo_*` tables and the constellation's
  `cedar_constellation_*`. Codebook blocks **are** registered
  (`18a_nest_enterprises`, `18b_nest_enterprise_relations`, appended to
  `codebook_master.csv` rather than rewriting it, backup
  `.bak_2026-09-02_pre_1072_tribally_owned_enterprises`). What remains is the
  chain in `docs/SHIPPING_RUNBOOK.md` — `87 → 25 → 27` — which rewrites
  publication state for **every** collection at once. **Deliberately not run
  here**: three other agents were writing to `data/clean` during this pass, and
  `25`'s curated-override list is already churning (the gate says so in its own
  message). It is one command for the integrator, and it ships the geography and
  constellation tables in the same pass.

**`code/845_regenerate_guard.py` CRASHES** and could not be run:
`TypeError: const_env() takes 1 positional argument but 3 were given`
(`845:418`, called from `scan_csv`). Mid-edit by its own workstream, not caused
here. Its instruction was followed anyway: `1072.write_csv` derives its header
as `CANONICAL + [c for c in live if c not in CANONICAL]`, so a column another
workstream adds to a NEST table survives a rebuild instead of being deleted.

---

## 2026-09-02 — WORKSTREAM NBOA-EXPAND (`code/1070`, `code/1073`), ANC / NHO / Alaska Native Village business directories

Full record: **`docs/NATIVE_BUSINESS_ANC_NHO_SWEEP_2026-09-02.md`**.
**Nothing was committed. Nothing was written to `data/clean/` or to the spine.**

**What it did.** 822 entities probed — every Alaska Native Corporation (191),
every Native Hawaiian Organization (210), every Alaska Native Village
government and remaining tribe 701 never reached (365), every Intertribal
Organization (56). Every one has a verdict in
`data/staging/native_business_sweep_1070/verdicts.csv`; 29 published a list,
243 answered and published none, 31 refused by terms or robots, 519 have no
usable site. Plus a zero-network mine of all **358** AS 45.55.139 audited
annual reports (`code/1073`), which shard E never saw — 41 village
corporations, 34 with named subsidiaries.

**1,106 rows staged** to
`staged_native_owned_businesses_2026-09-02.csv` in the exact 58-column
`native_owned_businesses.csv` schema, de-duplicated against the live file,
against shard E's 482 hand-adjudicated ANC edges (156 dropped), and against
itself. 221 further candidates are in `candidates_for_review_2026-09-02.csv`
rather than deleted. Both scripts' `selftest` prove all 14 invariants fire on
an injected violation; both `verify`s are clean.

**THREE THINGS ANOTHER WORKSTREAM SHOULD TAKE.**

1. **`cedar_web_map.csv` records 127 entities' URLs against a site that does
   not name them** — 86 of them Alaska Native Village governments pointed at a
   borough, a regional consortium or an ArcGIS FeatureServer — plus 6 hijacked
   or parked domains. Named per entity in `verdicts.csv` with the route tried.
   Not fixed here; that file is not this workstream's.
2. **A name made only of stopwords cannot be identity-checked from page text.**
   The village of **Council** was matched to `kawerak.org` because the word
   "council" is on every tribal website, and it produced six rows of navigation
   furniture before the guard existed. 14 entities in the spine have this shape
   (`Council`, `Eek`, `Ute`, `Koi`, `ʻAi Noa Foundation` …). `1070` now
   requires the domain to carry the name too, and records
   `NAME_CHECK_INDETERMINATE`. **Any other workstream doing a name check
   against page text has this hole.**
3. **`review/tribal_vendor_list_registry_2026-08-26.csv` was deliberately NOT
   appended to.** 701 owns it and its 359 rows are federally recognised tribes;
   these 822 entities are a different population. Merging `verdicts.csv` into
   it is an integrator decision, not an agent writing into another workstream's
   shared file.

**NOT OURS.** `code/62_no_regression_check.py` is RED and this workstream
wrote **zero** files into `data/clean/`: `tables_undocumented_in_codebook
3 → 20`, `tables_missing_from_27_SPEC 194 → 213`, `ship_tables_at_zero
13 → 19`, `SHIPPING LOST: advocacy_passthrough_2026-08-07.csv`, and the two
tables that stopped shipping (`hearing_bill_links` 465 → 464,
`native_bills_subject_sweep` 2,414 → 2,409). The same failures are already
named, with owners, in the `1072` NEST entry immediately above — the new
tables are the geography, constellation and NEST workstreams'. Recorded here
so that reading this entry alone does not imply the gate was green.

### ADDENDUM — the 1070 handoff, merged the same day

`code/1070_anc_nho_business_sweep.py` staged **583 `assertion_class = OWNERSHIP`
rows** for NEST (`data/staging/native_business_sweep_1070/held_for_nest_ownership.csv`),
the integrator having merged the 523 `RELATIONSHIP` rows into
`native_owned_businesses.csv`. NEST **merged** them rather than appending:

```
583 held -> 229 refused (unreviewed heading scrape) + 57 refused (shareholder-
owned, not corporation-owned) + 297 ingested -> 167 merged onto enterprises
NEST already held + 128 net new
```

`nest_enterprises.csv` 1,482 -> **1,610**; `nest_enterprise_relations.csv`
3,492 -> **3,789**. `518` still reports **READY 14 / 14**, `293` still reports
**zero findings in `1072_*`**, and `verify`/`selfcheck` are still 8/8.

**The 229 refused prose scrapes contained SEVEN NATURAL PERSONS' NAMES** off
ASRC's leadership page, alongside `Blank`, `No Results Found` and
`Employee Resources`. The sweep had flagged them itself
(`HEADING_SCRAPE_ON_A_DIRECTORY_INDEX`, *"review before resolving"*) and was
right to. Every refusal keeps its full 58 staged columns plus a `nest_refusal`
sentence in `data/staging/nest/sweep_1070_refused.csv` — flag, never delete —
so any of them can be reversed without re-harvesting. **Whoever owns 1070
should look at that file: the same scrape route also fed
`native_owned_businesses.csv`, and nothing in this pass checked whether those
person names reached it too.**

**A conflict check produced a plausible wrong number twice before it produced
the right one**, and the correction is a modelling fact about NEST's own
schema: `relationship` carries two orthogonal axes in one column. `wholly_owned`
/ `majority_owned` state the SHARE; `holding_company` / `operating_company` /
`division` state the ROLE; `subsidiary` states neither. v1 reported 37
audited-vs-web conflicts (35 were `wholly_owned` vs the *unspecified*
`subsidiary`); v2 reported 23 (21 were Calista's SHARE vs ROLE); v3 compares
within an axis and reports **2**, both Chugach, both real. **60 enterprises are
now corroborated by two independent evidence families**, which is the first
answer this project has to `ASSERTION_LAYER.md`'s finding that every fact rests
on exactly one source.

---

## 2026-09-02 — GRAIN-LEGISLATION: the anomaly count, the eight missing titles, and the scope column nobody replayed

`code/1092_bill_titles_residue_and_scope.py` (new) and
`code/1093_bill_votes_majority_anomaly.py` (new). Both declared in
`cedar_pipeline.KNOWN_ORDERINGS` at creation. Chain is now
**14 → 73 → 1092 → 890 → 1093**, enrichers last.

**THE ANOMALY COUNT IS 16, RE-MEASURED FROM THE LIVE FILE, AND THE
COMPOSITION IS 9 + 5 + 2.** An anomaly = a simple-majority reading of the
tally mispredicts the recorded outcome. 351 of 423 votes are testable;
`MAJORITY_YEA_BUT_REJECTED` 16, `MINORITY_YEA_BUT_AGREED` **0**, `N` 335,
`NOT_TESTABLE_NO_RESULT` 72.

* 9 `HOUSE_SUSPENSION_TWO_THIRDS` — the nine `docs/WHAT_IS_MISSING.md` names.
* 5 `SENATE_CLOTURE_THREE_FIFTHS` — S102-0315, S104-0027, S109-0531,
  S115-0399, S115-0402.
* **2 `SENATE_THREE_FIFTHS_NOT_IN_QUESTION_TEXT` — the two that moved the
  count.** `S108-0356` (2003-09-23, 49–45, *Motion Rejected*, senate.gov
  `majority_requirement` 3/5): a Congressional Budget Act point-of-order
  waiver on S.Amdt. 1734, *"To provide additional funds for clinical services
  of the Indian Health Service, with an offset."* `S114-0351` (2016-02-02,
  52–43, *Amendment Rejected*, 3/5): S.Amdt. 3030 to S. 2012 under a
  unanimous-consent 60-vote agreement. **Neither is a cloture motion and
  neither threshold appears in the question string** — both read `On the
  Motion` / `On the Amendment`. Both carry
  `threshold_agrees_with_official = N`; only the join to
  `bill_votes_official_verification.csv` can see them.

The classes are derived from ROW PROPERTIES — chamber, `threshold_required`,
question text, agreement with the official record — never from a list of vote
ids, so a rebuild that adds a Congress gets classified rather than
mislabelled. An anomaly outside the three classes is a **refusal to write**.

**Why a new column when 890 already had one.**
`result_reconciles_with_threshold` reads **Y on all 351 testable rows and N on
none**, so it cannot distinguish the sixteen from the 335. The anomaly was
explained and then became invisible. `result_contradicts_simple_majority`,
`result_anomaly_class` and `result_anomaly_basis` are what a buyer reads.
`bill_votes.csv` 68 → 71 columns, **423 rows in → 423 out**, proven each run.

**EIGHT TITLE-LESS BILLS, AND THE CAUSE WAS CEDAR'S SPELLING, NOT THE
SOURCE.** Every canonical congress.gov bill_type slug in `native_bills.csv` is
100% titled (`hr` 1651/1651, `s` 1332/1332, `hres` 38/38, `hjres` 23/23,
`sjres` 12/12, `sconres` 5/5). Every non-canonical slug was **0%** (`hre` 0/2,
`hjr` 0/1, `treatydoc` 0/2, `treatydocno` 0/3). `14_pull_cosponsors.py`
hard-codes an `ok_types` allow-list; `hre` and `hjr` are Voteview's
abbreviations for `hres` and `hjres` and fail it, and treaty documents are not
on `/bill` at all. Asked correctly — and on `/treaty/{congress}/{number}` —
**all eight answered HTTP 200 on the first attempt**, 18 GETs total, one
poller, hostlock taken and released, real User-Agent, `.part`-then-rename.
`bill_title` on `bill_votes.csv` **390 → 398 of 423**;
`TITLE_BLANK_IN_native_bills.csv` **8 → 0**.

Two treaty identifiers were **ambiguous** and were settled by evidence, not
plausibility. Voteview writes `TREATYDOC1134` and `TREATYDOC1173` with no
separator, so 1|134, 11|34 and 113|4 all read the first. A candidate was
accepted only where the treaty's own action list carried a Senate action on
the roll call's date AND `congressConsidered` equalled the vote's Congress.
`1134` = **Treaty Doc. 113-4** (Protocol Amending the Tax Convention with
Spain); `1173` = **Treaty Doc. 117-3** (Accession of Finland and Sweden to the
North Atlantic Treaty). Also note: `treaty.topic` is a CATEGORY
("Commercial"), not a title — the title is the `Treaty - Short Title` entry in
`treaty.titles`, and nothing else was accepted as one.

**THE HONEST FLOOR ON THE OTHER 25: 22 ARE FACTS ABOUT THE WORLD.** All 25
carry no `bill_id` and Voteview records no bill number for any of them
(verified against `HSall_rollcalls.csv`). 22 are votes on reservations to a
resolution of ratification — 17 Panama Canal Treaty, 4 Neutrality Treaty, 1
US-UK tax treaty — no bill, therefore no bill title: `SOURCE_DOES_NOT_PUBLISH`.
**3 name a numbered measure in their own question text** and are
`NOT_ACQUIRED`: `H100-0888` (H.Con.Res. 331), `S100-0452` (S.Res. 386),
`S100-0417` (six S.Res. en bloc). Their eight titles were fetched and are on
disk, **deliberately unpromoted**, at
`data/raw/external/congress_gov/1092_title_residue_unlinked.csv` — promoting
one means minting a `bill_id` and a `native_bills.csv` row and rebuilding
`n_rollcalls`, `native_bill_outcomes.csv` and both entity bridges, which is a
decision for `14_build_bills_votes.py` and not an enrichment. The next pass
starts at `ON_DISK_NOT_PROMOTED` instead of `NOT_ACQUIRED`. So: **33
title-less votes → 8 closed, 3 closable and staged, 22 unclosable and correct.**

**THE FOUND DEFECT: A BACKFILL RAN AND THE DERIVATION THAT DEPENDS ON IT
NEVER DID.** `bill_scope` was blank on **168 of 3,069** and none of the 168
was unrulable. 128 gained a `title` on 2026-08-05 and still said
`bill_scope_basis = no_title_available`; 32 came from `73 --sweep` with a
blank basis; 8 had no title. `93-hr-10337` — *"An Act to provide for final
settlement of the conflicting rights and interests of the Hopi and Navajo
Tribes…"* — was scored `no_title_available`. 1092 replays 14's OWN ruler
(imported from `14_build_bills_votes.py`, never re-implemented) over all 168.
`bill_scope`: `general` 2,417 → **2,569**, `tribe-specific` 484 → **500**,
blank 168 → **0**. `native_bills.csv` **3,069 rows in → 3,069 out**.

**FLAGGED, NOT FIXED — `bill_scope` now carries two ruler vintages.** The
spine has grown to 3,717 usable names. Re-running today's ruler over the
2,901 pre-1092 rulings changes **76** of them; those were NOT re-ruled,
because that moves a published `tribe-specific` count and is an owner
decision. `1092 verify` prints them every run. **Two of the causes are
spine-quality problems, not new knowledge:** an entity literally named
**"Tribal Self-Governance"** matches 14 generic bill titles and **"Native
Health"** matches 7 — names that generic arguably belong in the ruler's
`GENERIC` exclusion list, alongside `indian`, `tribe`, `nation`. The 168 rows
1092 ruled are stamped `scope_ruled_1092_2026-09-02` in `record_basis`, and
152 of the 168 came back `no_specific_entity_matched`, which is vintage-safe
in the only direction that matters — a smaller spine cannot produce a match a
larger one did not.

**EVERY CHECK PROVEN TO FIRE AT THE FILE LEVEL**, not only in `selftest`:
inject into the live CSV, assert exit 1 AND that the NAMED invariant appears,
restore from a literal path (never a glob — the 163 incident), assert exit 0.
1092 C1–C5 and 1093 D1–D5, ten for ten. 1093's D5 is the one that matters
after a rebuild: it exits 1 when 890's threshold columns are absent rather
than reporting a clean result it did not measure.

**STALE NUMBERS CORRECTED IN PLACE** rather than left to look authoritative:
890's docstring and its two codebook variable descriptions (`bill_title`,
`bill_title_source`) stated 390/8 and now state 398/0, refreshed in
`codebook/10_bills_votes.csv` and `codebook_master.csv` by
`1092 codebook` (130 → 130 and 5,199 → 5,199 rows, conserved).
`docs/methodology/legislation.md` had **five** stale claims: BLOCKED (it is
`READY`, 11 tables, per `518`), the nine-anomaly paragraph, "no
`threshold_required` column exists", "390 of the 423", and the `bill_scope`
distribution. All corrected, with the superseded figure kept beside the new
one. `docs/WHAT_IS_MISSING.md`'s CLOSED box for this dataset had already been
corrected to sixteen by the `890` pass; its Item 1 figures (390 of 423, 8
`TITLE_BLANK_IN_native_bills.csv`) and its cross-dataset table row 7 were
updated here to 398 / 0, and item 2's heading now says CLOSED. **Its body
prose still proposes the wrong derivation** — "87 votes whose `question`
contains 'suspend'", which catches `S095-0741` (a Panama Canal reservation
reading "…SHALL BE SUSPENDED UNTIL SETTLEMENT") and mistypes `H095-0549` (an
*order a second* motion, decided by majority). That prose is left verbatim by
that file's own convention — *"the read below is left exactly as written"* —
and the correction sits in the box above it.

`code/770_sample_extracts.py`'s `legislation` SHOW list gains
`result_contradicts_simple_majority`. **770 was NOT run**: it regenerates
every dataset's sample and four other workstreams had live processes against
`data/clean` during this pass. The list change is inert until the integrator
runs it, which is the point.

### The gates, and who owns the red

`py -3 code/518_dataset_readiness.py` → **READY  legislation  11 tables**.
`1092 verify`, `1092 selftest`, `1093 verify`, `1093 selftest` → **exit 0**.

`py -3 code/293_lint_bug_classes.py` → **exit 1**, and
`py -3 code/62_no_regression_check.py` → **exit 1**. Standing rule 15 says name
the owner with a measurement rather than record it as pre-existing and walk on.
Measured: **`1092_*` and `1093_*` contribute ZERO findings to `293`** (0 of
226 findings name either file). The 27 new lint instances are
`1098_entity_rel_counterparty` (4), `1060_splink_pilot` (3),
`1030_sec_edgar_native_transactions` (2), `1031_ancsa_45_55_139_annual_reports`
(2), `1086_faads_award_key_promote` (2), `873_build_aiannh_crosswalk` (2),
`992_newsletter_deal_candidates` (2), `1107_punchlist_claim_verify` (2), and
one each in `1011`, `1081`, `1085`, `1099`, `1101`, `1104`, `846`, `852`,
`980`, `518`, `30`, `870`, `871`, `1077`. `62`'s
`files_with_columns_lost_vs_backup = 2` is `native_fi_roster.csv` (lost
`in_cicd_nafi_map`) and `cedar_entity_spine.csv` (lost `cicd_verified`), both
against `.bak_2026-09-02_pre844` — script `844`, not this workstream. The
shipping losses (`hearing_bill_links` 465 → 464,
`native_bills_subject_sweep` 2,414 → 2,409, `advocacy_passthrough_2026-08-07`
gone) predate this pass; `native_bills_subject_sweep` already read 2,409 in
`docs/methodology/legislation.md` before it started. **Neither table this pass
touched lost a row or a column: `bill_votes.csv` 423 → 423 and 68 → 71
columns; `native_bills.csv` 3,069 → 3,069 and 29 → 29 columns.**

---

## 2026-09-02 — workstream DEALS-MERGE-1088: the staged deals merge, and who owns the red gate

`code/1088_merge_staged_deals.py`. **312 staged candidates in, 138 admitted,
174 refused with a named reason, every refusal kept whole in
`review/deals_1088_refusals.csv`.** `deals_classified.csv` 935 -> 1,073 rows;
`Announced_Value_USD` $45,195,917,316 -> $47,880,355,533. Conservation proved
row-for-row: **0 pre-merge `Deal_ID`s lost, 0 pre-merge values changed, 0
columns lost.** Full account in `docs/methodology/deals.md` section 5b.

### Three standing rules this pass earned

**1. A PRESENT-TENSE OWNERSHIP MAP INVERTS THE INTRA-FAMILY TEST ON A PAST
ACQUISITION.** Bering Straits bought Alaska Gold Company from NovaGold in 2012;
Alaska Gold is a BSNC subsidiary today, so a shared-hub test calls the 2012
purchase an internal relabelling and destroys the event that created the
relationship. **A family map built from today's ownership refuses exactly the
acquisitions that succeeded.** The obvious repair — "does the sentence name an
organisation outside the family?" — is circular for the same reason: the target
is inside the family by the time the map is built. It still refused eleven ASRC
Industrial acquisitions, UIC/Johansen Construction, Choggiung/Bristol
Industries and Shee Atika/Eikon Research. What works is not topology but what
the passage DOES: a transfer verb overrules the topology, a reorganisation verb
confirms it, and an identifier flip with no sentence has only the topology to
go on. The gate went **34 -> 24 -> 2** refusals across three versions.

**2. `cedar_constellation_edges.csv` IS NOT AN OWNERSHIP SOURCE.** All 3,153
rows carry `is_ownership_claim = N`; its tiers are `registered_with` (2,365),
`declares_service_to` (588), `managed_under_contract` (78), `located_within`
(78), `chartered_by` (44). **`code/1071_identifier_driven_deal_sweep.py` builds
its family closure from that file at every tier and never reads
`nest_enterprise_relations.csv`, which holds the 3,613 actual ownership edges.**
Reported here, not repaired — `1071` is not this workstream's file.
Related, in `nest_enterprise_relations.csv`: an `affiliation` /
`shareholding_or_ancestry` edge (`NESTREL-291D0B2DBBCBD1`) records **Huna Totem
Corporation** — an independent Hoonah village corporation — under **Doyon,
Limited**, quoting Doyon's own *"Operating more than a dozen for-profit
companies"*. It cost five real Doyon rows before it was caught. Owner: `1072`.

**3. A MERGE SCRIPT THAT DE-DUPLICATES AGAINST ITS OWN PREVIOUS OUTPUT IS NOT
IDEMPOTENT, IT IS SELF-ERASING.** Measured on the second run of `1088` before
the guard existed: it saw its own 144 rows in `deals_classified.csv`, refused
them all as duplicates, admitted 64, and would have rewritten the additions
file at 64 rows — so the next rebuild would have silently lost 80. Every
comparison now excludes rows whose `_source_file` is the script's own output,
and the run prints that it is doing so.

### Gate status, and who owns the red (standing rule 15)

`62_no_regression_check.py` exits **1**. `293_lint_bug_classes.py` exits **1**.
**Neither is owned by this workstream**, and here is the measurement:

* `293`: `1088_merge_staged_deals.py` appears in **0** findings. It appeared in
  one — a class-2c `skipped += 1` in `build_family_map` — and that was fixed by
  naming every skipped edge class with a count and a worked example before this
  entry was written.
* `62` `shippable_grain_unstated` named `deals_press_edgar_ancsa_additions.csv`.
  **Fixed**: `GRAIN_DEALS_MERGE` declared in `512_build_dataset_contracts.py`,
  `Deal_ID` confirmed 144 distinct / 0 blank on the full file, 0 literal
  duplicate rows.
* Everything else red in `62` is other workstreams running concurrently in this
  same session — the lint rises are named per script by `293` under
  `NEW <class> instance` (`1098` x4, `1060` x3, `1030`, `1031`, `1086`, `873`,
  `992`, `1107` x2 each, plus singles), and
  `files_with_columns_lost_vs_backup = 2` is `native_fi_roster.csv` and
  `cedar_entity_spine.csv` against `.bak_2026-09-02_pre844` — script `844`.
* **No table this pass touched lost a row or a column.**
  `deals_classified.csv` 935 -> 1,079 rows, 52 -> 52 columns.

### Verify and selftest

`py -3 code/1088_merge_staged_deals.py verify` reads the SHIPPED files, not the
writer's own variables, and exits 1 on breach. `--selftest` injects one
violation of each named invariant into a copy and asserts both that exit is 1
AND that the named invariant is what fired, then asserts the untouched files
still return 0. **5 of 5 invariants fire:** no source link; a ceiling in
`Announced_Value_USD`; neither a date nor a year; a blank `Event_Date` whose
`Date_Basis` does not say why; a refusal with no stated reason.

## NAGPRA SPLIT-ARTEFACT PASS - the fabrication class was NOT fixed, only narrowed (2026-09-02)

`code/1084_nagpra_split_artefact_audit.py` (new, `claim`ed) and
`code/1104_nagpra_affiliation_rule_audit.py` (new, `claim`ed). Measurements in
`docs/NAGPRA_SPLIT_ARTEFACTS.json`,
`docs/NAGPRA_AFFILIATION_RULE_AUDIT.json`, `review/nagpra_alias_independence.csv`.

**The headline, because the next agent must not read `1077` as closed.**
`1077` fixed *"Tourism, Columbia, SC"* by splitting on `;` **where the title
carries one**. Only **64 of 6,792** titles do. The other 6,728 still run
`LEGACY_SPLIT_RE`, **328 of them split**, and the same fabrication is live:
`02-7009`, `04-22830`, `2026-15500`..`2026-15524` (11 notices) each ship
`Louisiana Department of Culture, Recreation` **and**
`Tourism, Division of Archaeology`, from the single real name *Louisiana
Department of Culture, Recreation, and Tourism, Division of Archaeology*.
**The word `Tourism` is a fabricated institution in this dataset today.**
The permanent fix is in `1077.split_institutions` / `77`'s
`institution_parts`, and it is NOT made here.

**77 of 7,234 bridge rows (1.06%) flagged; 0 rows deleted; 55 carry a
verbatim-recoverable repair.** Row conservation 7,234 -> 7,234, ids identical,
11 -> 16 columns, all five new. `provegates` proves **I1..I6 each FIRE** on an
injected breach and are silent on the restored table.

**`data/clean/nagpra_notices.csv` carries the SAME fabrication on 51 notices**
in `institution_name` / `institution_primary` / `institution_names_all` and is
deliberately NOT written by `1084` - a second writer on `1077`'s six in-place
columns is the class-6 hazard. Declared in `cedar_pipeline.KNOWN_ORDERINGS`:
`1077` rebuilds the bridge wholesale, `1084` enriches it, and **1084's five
columns do NOT survive a 1077 run** - re-run it.

**The three affiliation rules were audited and NOT relaxed. All three hold.**
R1: all 51,579 bridge rows measured against their own cached FR full text,
**0 absent**; 226 differ only by a `;` the parser turned into a `,` inside a
parenthetical and 1 by a space where an HTML anchor closed. R2: **0** aliases
in `entity_aliases.csv` are sourced from this dataset, so nothing entered the
identity layer below the bar; the republication test folds 6,792 notices to
**6,519 families** and demotes 16 alias candidates, 0 of them across the
three-notice line. R3: every free-text notice column is **>= 99.9% verbatim**
in its own source.

### Gate attribution

`62` exits 1 and `293` exits 1. **Neither is owned by this pass, and the
measurement is that the word `nagpra` appears ZERO times in `62`'s output.**
`62` names every new lint instance per script and the whole list is other
workstreams: `1011` (class1), `1060` x3, `1085`, `1086`, `846`, `852`, `873`,
`992` (class2c/class3), `1030`, `1031` (class4). `1084` and `1104` each
contributed exactly one line and **both are waived with a reason on the line
above** - `class7` a selftest fixture id, `class3` an exclusion of
already-keyed rows rather than a positive-outcome read - and neither appears
in `62`'s NEW-instance list. `files_with_columns_lost_vs_backup = 3` is
`native_fi_roster.csv` and `cedar_entity_spine.csv` against
`.bak_2026-09-02_pre844` (**script `844`**) and `prime_contracts.csv` against
`.bak_2026-09-02_pre_1085_prime_psc_desc_repull` (**script `1085`**).
`codebook_undocumented_public` is **0** - the five new columns were written to
`data/clean/codebook/11d_nagpra_notice_institutions.csv` AND kept in step in
`codebook_master.csv`, so `1108`'s K1 (master == fragments) stays true; 11 ->
16 fragment rows, 5,444 -> 5,449 master rows, 0 replaced, and a re-run is a
no-op. `518` still reports `nagpra` **READY**, now 5 tables.

### A fourth rule, found by auditing the script's OWN admitted output

**AN ARTICLE DATE IS NOT A TRANSACTION DATE, AND EVERY PRESS ROW IN THIS
PROJECT IS DATED BY ONE.** All 96 tribal-press rows the first pass admitted
carried `Date_Basis = "post date published by the site's own REST API for this
article"`. Auditing them against their own sentences found **14 that name a
year two or more before the year they were filed under** — `BSNC acquired the
Alaska-grown company in August of 2015`, filed 2020.

The naive gate over-refuses: *"Chugach Commercial Holdings: Established in
2014"* inside a genuine 2026 acquisition announcement is background, and
refusing it loses a real transaction over a date that is not its date. **Gate
G11 therefore fires only when the earlier year sits within 60 characters of a
transfer verb** — where a transaction year lives in a sentence and where a
founding year does not. 9 refused, 5 kept with an extended `Date_Basis` naming
the other year and stating the article date is not known to be the transaction
date.

**Six of the nine had already been merged.** They were WITHDRAWN, not deleted:
whole rows to `review/deals_withdrawn_duplicates.csv` (3 -> 9), which
`88_build_deals_taxonomy.withdrawn_ids()` honours on every rebuild — the route
`MA2020-008` took. Row and money conservation asserted:
1,079 -> 1,073 rows, 52 -> 52 columns, `Announced_Value_USD` **unchanged**
because all six carried $0. Named individually: `NLTR-2016-003`,
`NLTR-2018-009`, `NLTR-2020-003`, `NLTR-2021-008`, `NLTR-2024-010`,
`NLTR-2026-013`.

**The habit this rewards is field-guide habit 3 applied to your own output:**
the gate set was written, run, and then its ADMITTED rows were read next to
their sources. Four of the five rules above came out of that reading, not out
of the specification.

---

## 2026-09-02 — GATE 62 IS RED, AND THE `_entity_layer` DEEPENING PASS OWNS NONE OF IT. NAMED, WITH THE MEASUREMENT.

*Standing rule 15 says a FAIL is stop-work and that "pre-existing, not mine" is
not a disposition — name the owner with a measurement or fix it. This is the
naming. Written by the `_entity_layer` / `nest` / `native-owned-businesses` /
`nonprofits` deepening pass (`code/1098`–`1102`,
`docs/ENTITY_LAYER_DEEPENING_2026-09-02.md`).*

**What this pass touched, so the scope of the claim is checkable:** five tables,
enriched in place, all rows conserved and no column lost —
`entity_relationships.csv` (16→25 cols), `cedar_identifier_ledger_final.csv`
(22→26), `native_owned_businesses.csv` (58→74), `np_orgs.csv` (57→66),
`nest_enterprises.csv` (59→68) — plus `data/staging/nest/evidence_conflicts.csv`
(9→14, 2 rows), an APPEND of 47 rows to `codebook_master.csv`, five `review/`
registers, one marked ADR block, and five doc appends. **No table was created,
no table was rebuilt, nothing was shipped, nothing was committed.**

### The eleven red lines, and who owns each

| red line | owner, measured |
|---|---|
| `files_with_columns_lost_vs_backup = 2` | **`code/844`.** The gate names both: `native_fi_roster.csv` 23→22 (lost `in_cicd_nafi_map`) and `cedar_entity_spine.csv` 44→43 (lost `cicd_verified`), each against its own `.bak_2026-09-02_pre844`. **This pass wrote to neither file.** Standing rule 12: re-run the enricher, then re-run the gate. |
| `lint_new_defect_instances = 26`, and the `lint_class1/2c/3/4/5/7` rises | **not one named instance is from `1098`–`1102`.** `293` names them: `1011_cross_dataset_reconciliation.py` (class 1), `1060_splink_pilot.py` (2c ×2, class 3), `1085_prime_psc_desc_repull.py`, `1086_faads_award_key_promote.py`, `846_session_audit.py`, `852_extend_constellation_edges.py`, `873_build_aiannh_crosswalk.py` (2c), `992_newsletter_deal_candidates.py` (class 3), `1030_sec_edgar_native_transactions.py`, `1031_ancsa_45_55_139_annual_reports.py` (class 4). **Re-measured after this pass's last write: `py -3 code/293_lint_bug_classes.py` returns ZERO findings in `1098`, `1099`, `1100`, `1101` and `1102` across all seven classes.** Three class-2a and three class-2c findings WERE raised against this pass's first drafts and were **fixed, not waived** — the 2a by replacing `setdefault` with plain assignment (these enrichers recompute their own columns and must not carry a stale value forward), the 2c by writing the refusal reason onto the row rather than only into a counter. |
| `regenerate_new_unsafe_writers = 1` | **`code/1107_punchlist_claim_verify.py`**, named by `845`: markdown → `docs/datasets/_PUNCHLIST_CLAIM_AUDIT.md`. All five scripts in this pass derive their header from the live file (`fields = list(live_fields) + [c for c in NEW if c not in fields]`) and `845` class 1 and class 3 are both **0**. |
| `tables_missing_codebook_block 3→22`, `tables_undocumented_in_codebook 3→21`, `tables_missing_from_25_TABLES 179→211`, `tables_missing_from_27_SPEC 194→218`, `tables_missing_notes_contract 14→22`, `ship_tables_at_zero 13→21` | **new tables from other passes.** The gate lists them: `geo_award_county_crosswalk.csv` (1,050,968 rows), `geo_place_county_crosswalk.csv`, `geo_county_two_sums.csv`, `geo_county_dim.csv`, `geo_point_aiannh_assignment.csv`, `geo_aiannh_dim.csv`, `dear_tribal_leader_letters.csv`, `entity_dated_public_facts.csv`, `gaming_web_harvest_*`, `cedar_entity_freshness.csv`, `tribal_newsletter_*`. **This pass created no table in `data/clean`.** Its outputs are new COLUMNS on five already-registered tables, and all 47 of them were appended to `codebook_master.csv` with descriptions — `codebook_undocumented_public` is still **0** and `duns_marked_publishable` is still **0**. |
| `contract_violations = 11`, `contract_orphan_shippable = 7` | same population as the row above — an unregistered new table has no owning collection and no contract. `py -3 code/518_dataset_readiness.py` run after this pass: **READY 13 / 14**, and all four datasets this pass touched (`_entity_layer`, `nest`, `native-owned-businesses`, `nonprofits`) are READY. The single BLOCKED is `deals`, on `C1 grain UNSTATED` for `deals_press_edgar_ancsa_additions.csv`. |
| `rulings_unapplied 1,215 → 2,894` | **this pass applied no ruling and minted no tier.** Everything it found is FLAGGED and filed: 13 ledger collisions, 1 owner disagreement, 8 NEST parent contradictions, 25 duplicate groups, 535 nonprofit key reviews — all in `review/*_2026-09-02.csv`, with three items appended to `review/OWNER_DECISION_QUEUE.md` (EL-1, EL-2, EL-3). A proposal on a row is not an unapplied ruling; `cedar_rulings.csv` was not written. |
| `SHIPPING LOST: advocacy_passthrough_2026-08-07.csv` gone from `data/clean`; `hearing_bill_links.csv` 465→464; `native_bills_subject_sweep.csv` 2,414→2,409 | none of the three was read or written by this pass. |

### The one thing worth generalising from this

**Eleven red lines, and the gate itself named the owner of every one.** That is
what the per-metric naming in `62` bought: the six sessions that stepped around
`codebook_undocumented_public = 45` had to guess whose it was, and this took one
grep. The remaining cost is that a red gate is still stop-work for *everyone*,
so a metric another agent broke blocks the agent who reads it next — which is
the deadlock the `handoffs_failed_only_on_this_gate` split was written to break,
one level up. Worth the integrator's attention: **`844`'s two lost columns are
the cheapest of the eleven to clear**, and clearing them removes the only
regression on this list that is a data loss rather than a registration gap.


---

## 2026-09-02 — workstream `newsletters`: the corpus taken to the shipping standard, and two web-map defects found by a new invariant

*Scripts `990`, `991`, `995` (owned), `1105_newsletter_corpus_ship.py` and
`1106_tribal_election_survey.py` (both claimed atomically via `1050 claim`).
Nothing committed. Ownership and the shared-file edits are declared in
`docs/ARCHITECTURE_DECISIONS.md` under ADR-023-NEWSLETTERS.*

### What the corpus is now

| | before this pass | after |
|---|---:|---:|
| rows in `tribal_newsletter_corpus.csv` | 1,650 | **1,889** |
| **publication channels** (`record_status = publication_channel`) | 1,195 | **1,394** |
| entities publishing at least one | 650 | **694** |
| coverage found / attempted_none_found / not_probed | 650 / 440 / 455 | **694 / 480 / 371** |
| federally recognized tribes found | 223 / 349 | **264 / 349** |
| entities that operate a live site, are in scope, and were never probed | 79 | **0** |

`991` was re-run to exhaustion: 312 entities attempted in total, 1,516 requests,
**0 hosts quarantined** for serving one body to many URLs.

### The blocker the builder named, measured rather than argued

NHO coverage was 8% and the question was whether to run a second pass or write
a caveat. **Both, and the measurement is what decided it.** All 102 NHOs that
operate their own site have now been probed on every machine-readable route;
11 publish. The other **108 of 210 have no website of any kind** — 81 no URL at
all, 17 only a Wayback capture of a dead site, 10 only a ProPublica IRS profile.
The class rate is 5%, the rate among NHOs with a site is 11%, and both are true
statements about different denominators. `SOURCE_DOES_NOT_PUBLISH`, not a
backlog.

Village corporations were the mirror image, and the stated 31% was hiding the
finding: only **38 of 173 operate a website**, but **54 publish**, because 21
were found on the **State of Alaska DBS STAR portal**, where ANCSA corporations
file shareholder communications by statute. A corporation with no website can
still have a statutory publication channel — on somebody else's host.

### THREE COLUMNS ADDED, BECAUSE THE ANSWER TO A CAVEAT IS A COLUMN

* **`record_status`** on the corpus. The file held two record types under one
  schema and the only way to tell them apart was a `channel_type` set held in a
  DIFFERENT script plus a string-match on the prefix of `note`. A reader
  counting rows got 1,889 "tribal newsletters"; the channel count is 1,394.
* **`site_url_class`** on the coverage table — `own_live_site`,
  `wayback_snapshot_only`, `propublica_irs_profile_only`, `social_media_only`,
  `third_party_api_endpoint`, `no_url_anywhere`. This is the column that makes
  every coverage rate above readable.
* **`source_defect`** on the staged BIA leader table (see below).

`995` now reads the channel count off `record_status` instead of holding its own
copy of the vocabulary, so the published figure and the file cannot drift.

### THE NEW INVARIANT, AND THE TWO DEFECTS IT FOUND ON ITS FIRST RUN

`990` invariant 10, **PROBEABLE_FRONTIER_NOT_CLOSED**: fail the build if any
in-scope entity operates a live site and has never been probed. "We finished
the frontier" is now a check rather than a sentence in a document. It failed
immediately, twice, and both were real:

**1. A WAYBACK URL OUTRANKED A LIVE ONE.** 991's site preference ranked
web-map URLs by `url_type` with no preference against `web.archive.org`, so an
archive capture could win — and the wayback skip, which exists for entities
whose ONLY known URL is a snapshot, then fired on entities whose FIRST-RANKED
one was. **Fort Independence, Poarch, Pueblo of Pojoaque, Redding and Ute
Mountain** all run live sites that no route had ever touched. Archive hosts now
sort to the back of the preference order.

**2. `has_live_site` WAS `yes` FOR 45 NATIONS WITH NO WEBSITE.** Once archive
URLs were demoted, the next-ranked "website" for 45 Alaska Native Villages was
the **BIA Tribal Leaders Directory ArcGIS FeatureServer query** that shard K had
used to READ them — `services1.arcgis.com/.../FeatureServer/0/query?...f=json`.
**A response about you is not a site you operate.** Probing it would have asked
a federal API for a newsletter, 45 times. This is the field guide's signature
defect in a new place: the check produced a number, the number was plausible,
and it was about something else.

### A CHECK OF MINE WAS WRONG AND FIRED ON 88 REAL ROWS BEFORE IT SHIPPED

1105's privacy invariant first scanned `note` for private-life terms. It hit 88
rows, every one of them **Cedar's own description of a source**: "The Council
... carries member-village council news, obituaries and program notices." That
is not an obituary. **Saying that a publication carries obituaries is not
extracting one**, and a check that deleted those sentences would have made the
corpus less truthful in the name of privacy. Rescoped to where a leak would
actually land — `publication_name`, `channel_url`, `recent_issue_urls`, where a
slug like `/2024/03/obituary-jane-doe/` would appear. 0 hits, and the selftest
now asserts BOTH that a planted slug fires AND that a descriptive note does not.

### Gates

`990 verify --selftest`: **12 invariants, 12 selftests fire, exit 0.**
`1105 verify --selftest`: **6 ship invariants plus a clean-fixture assertion,
all fire, exit 0.** `1106 verify --selftest`: **5 invariants plus clean fixture,
all fire, exit 0.**

Codebook: `19a_tribal_newsletter_corpus` (29 variables) and
`19b_tribal_newsletter_coverage` (16), appended to `codebook_master.csv`
(5,199 → 5,244); both tables match their block at **1.000**, well over the 0.60
threshold. Conservation: 18 rows in `cedar_harvest_conservation.csv`, three
funnels, each asserting its dispositions sum to its input.

### The deals out of the press are not this collection

`1088_merge_staged_deals.py` (another agent, same day) merged the staged
newsletter candidates into `deals_classified.csv`, 935 → 1,079. That is the
right home for them. The `newsletters` collection regex `^tribal_newsletter_`
deliberately cannot reach them.

### Elections — a survey, not a dataset, per the owner's own scope

`docs/TRIBAL_ELECTIONS_SOURCE_SURVEY.md`, written by `1106`.

**The route the brief expected does not work today: the newsletter text was
never retained.** `_documents.jsonl` holds url, host, md5, byte count and a
candidate COUNT for all 1,077 fetched documents — no body. The
`deal_candidates*.csv` files hold only sentences that matched a DEAL pattern.
Extracting elections from the press means re-fetching everything, then OCR, then
a per-document human read.

**The route that does work was already half on this machine, one column deep.**
Shard K had pulled the Alaska slice of the **BIA Tribal Leaders Directory**
ArcGIS layer (227 records, one HTTP request per record) to read village
addresses, and nobody had noticed the same layer carries **`dateelected` and
`nextelection`**. The national layer is **602 records and two HTTP requests**.
Staged at `data/staging/tribal_governance/tribal_leader_terms_staged.csv`:
**587 of 602 resolved to the spine (98%)** by exact normalised name, 487 carry
`date_elected`, 468 carry `next_election`. The 15 unresolved are 14 ambiguous
name matches — recorded as ambiguous and **never keyed**, because the exactness
of a name says nothing about the correctness of the link — and one with no
match. Personal contact fields (email, phone, fax, physical and mailing
address, coordinates) are dropped before anything is written: the office is
public, the person's contact details are not ours to redistribute.

**It is one leader, not a council, and a snapshot, not a history.** The BIA
overwrites the layer in place, so `date_elected` is the current term only.
Turnover exists only if we start snapshotting now. Council composition needs
~200 per-consortium pages, each a different layout, with no national aggregator
— the 31 Bristol Bay councils and 235 named officers already parsed in
`shard_k/bbna_tribal_councils.jsonl` are the shape and the price of that work.

**One upstream BIA defect, flagged not deleted:** Ottawa Tribe of Oklahoma is
published with its chief elected `2026-05-27` and the next election
`2026-05-02` — 25 days earlier. Both dates kept verbatim, `source_defect`
names it, and 1106's E2 fires on any inverted pair that is NOT so flagged.

---

## LOBBYING — the amendment-supersession defect closed, and the Schedule C "backlog" measured away (2026-09-02, script 1091)

**Scripts:** `code/1091_lobby_amendment_supersession.py` (new, claimed via
`1050 claim`), plus three rows added to `code/86_build_series_breaks.py`'s
`BREAKS` list and two caveat strings corrected in
`code/27_build_dataset_manifests.py`. Ran `86`, `87`, `27`, `287`, `99 --steps
irs-deflate64`, `99 --steps schedc-lobbying`. **No commits.**

### A — the defect the methodology described and the file had never had

`docs/METHODOLOGY_LOBBYING.md` said amendments were applied over the originals
they replace. `native_entity_lobbying_disclosures.csv` did not do it.

* **1,135** groups on the doc's own key
  `(client_id, registrant_id, filing_year, filing_period)` hold an amendment
  beside a non-amendment. **That count reproduces to the row.**
* **The doc's "$28,961,112 — 4.0%" reproduces under nothing.** The string
  appears in `docs/methodology/lobbying.md` twice and in no script. Eight
  candidate definitions were measured: $33,218,483 / $36,347,996 /
  $39,183,189 / $40,119,485 / $45,805,356 / $47,866,925, plus two filtered
  variants that move further away. **Withdrawn and replaced with
  $37,349,254.01 (5.15% of $725,743,974.52) over 1,064 rows.**
* **The doc's key is unsafe as written.** It buckets a REGISTRATION with the
  REPORT that follows it — group `('153096','43651','1999','mid_year')` holds
  a $0 Registration, a $0 Registration-Amendment, and a $60,000 Mid-Year
  Report. A naive "amendment wins" rule keeps the $0 row and deletes the
  $60,000 one. The key therefore carries a fifth part, the form family, and
  **still refuses** in the 294 groups holding more than one non-amendment row.

**Resolved by implementing, as FLAGS.** Four columns, 40 → 44:
`supersession_group_id`, `supersession_status`, `is_superseded`,
`superseded_by_filing_uuid`. **Row conservation 27,825 → 27,825; money
conservation on `income_usd` / `expenses_usd` / `spend_usd` to the cent**,
printed before and after and re-provable with `verify`. **No row deleted, no
existing cell changed, and no new money column created.** 129 rows carry an
`AMBIGUOUS_*` status ($3,649,798) where which filing restates which is not
knowable from the LDA fields Cedar holds: they stay **in** the total, flagged,
never guessed.

`selftest` proves **8 of 8** invariants FIRE — I1 row, I2 money, I3 cell, I4
key, I5 superseder resolves, I6 one survivor per group, I7 the drop accounts
exactly, each by injecting one synthetic violation, asserting the NAMED
invariant among the failures, restoring and asserting clean. **The first draft
of I6 printed SILENT on a real violation**: the fixture picked a superseded row
out of a two-row group, so un-superseding it emptied the group of superseded
rows and I6's precondition went false. AGENT_FIELD_GUIDE §3 habit 1, live.

**A second §3 instance, caught by running the gate rather than trusting it.**
`287_build_dependency_manifest` filed 1091 under
`readers/native_entity_lobbying_disclosures.csv` — a script that *rewrites*
that file, invisible to the manifest that exists to stop a rebuild reverting an
enricher. Cause: `cedar_pipeline.declared_io` follows a bound name and looks
for a write verb on the lines that mention it, and the write went through a
`path=TARGET` parameter. Fixed by naming the write on `TARGET`'s own lines
(and by calling `write_codebook_block(CODEBOOK_MASTER, …)` explicitly instead
of looping over a tuple). 1091 now appears in `writers`, in `contested_files`,
and in `build.py plan lobbying` PHASE 2. **Anyone adding an enricher in this
repo should check the manifest actually sees it.**

**The `aggregation_safe = 1` half is NOT closed and is the integrator's.**
`517` classes the table `SAFE_TO_AGGREGATE` on a primary-key and
literal-duplicate test, and both still pass — the classification is correct on
its own terms and it is still the field a buyer's tooling reads first. Either
`517` gains *additive under a stated predicate*, or the lobbying contract in
`512` declares one. Both files are the integrator's; the measurement is in
`docs/MONEY_TOTALLING_RULES.md` under `LOBBY-SUPERSESSION`.

### B — the three totals hold, and the shipped surface did not warn about them

All three re-measured 2026-09-02 and all three reproduce exactly:
$645,052,868.51 (registrants, 653 rows) · $680,561,640.52 (panel, 5,001) ·
$725,743,974.52 (filings, 27,825). **The documentation was right. The shipped
files were not.** `dist/04_lobbying/native_entity_lobbying_disclosures.NOTES.md`
described `spend_usd` as "Reported lobbying spend for the filing period" with
no warning, and `tribe_year_lobbying_panel.NOTES.md` described
`total_lobbying_spend_usd` as, in full, **"Amount."** Neither shipped note
mentioned amendments or the other totals. A buyer could innocently sum to a
wrong number, and could innocently add two tables.

Fixed at the generator's inputs, not by hand-editing generated files:
`data/clean/series_breaks.csv` **24 → 27 rows, zero pre-existing rows lost**
(three rows added to `86`'s `BREAKS`; `86` rewrites that file wholesale from
that list, so appending to the CSV would not have survived), and the
`spend_usd` / `total_lobbying_spend_usd` descriptions rewritten in
`codebook_master.csv` and `data/clean/codebook/04_lobbying.csv`. `87` then
renders both as a `## Comparability` block and a codebook row in the shipped
notes. **There is now a FOURTH figure** — $688,394,720.51, `WHERE
is_superseded = 0`, the only additive one at filing grain — and it sits $7.8M
from the panel's $680.6M by coincidence, which is the likeliest way someone
gets this wrong. It is named as such everywhere it appears.

Corroboration for the key: `lobbying_registrants.csv` has been doing
supersession since 2026-08-26. Its shipped codebook says *"Deduplicated to one
value per (registrant, client, year, reporting period), taken from the filing
with the latest dt_posted, because an amendment supersedes what it amends."*
**The rollup did it; the filing table it was built from did not.**

### C — Schedule C: 21.3% was a stale number, not a backlog

`512`, `27`, `132` and `MONEY_TOTALLING_RULES.md` all state **32,218 indexed /
6,870 retrieved / 21.3%, "Cedar's own fetch backlog"**. Measured before opening
a socket, per AGENT_FIELD_GUIDE §5: **28,677 XML were already on disk.**
`code/860`'s full-history pull ran 2026-09-01 23:5x–2026-09-02 00:10, extracted
21,807 returns, and nothing re-parsed them. `ON_DISK_NOT_PROMOTED`, not
`NOT_ACQUIRED`.

One real fetch was still owed and was run under one-poller discipline
(`logs/_HOSTLOCK_apps.irs.gov.json` was released 04:10Z, no peer on that host,
claimed and released again): **691 returns had been logged
`indexed_but_absent_from_archives` when they were really DEFLATE64 members
CPython's `zipfile` cannot decode.** `--steps irs-deflate64` downloaded the six
affected archives one at a time, deleted each after extraction, and **recovered
472**. 6 archives, ~1GB peak, 88GB free.

```
                        before        after
XML on disk              6,870       29,149    (index 32,218 -> 90.5%)
parsed into the table    6,870       29,149    (+22,279 rows)
returns with a $         132          607
lobbying_usd_headline    $3,325,511   $16,455,891
2019 coverage            PARTIAL      FULL
```

**The 3,069 that remain are NOT a fetch backlog and must not be reported as
one.** 775 are `990T` (772) and `990PR` (3) — Schedule C does not exist on
those forms, `SOURCE_DOES_NOT_PUBLISH`, and `99` excludes them by design.
2,294 were requested and are absent from every IRS ZIP published for their
year, logged per object. 2017 (912) and 2022 (1,430) carry 2,342 of the 3,069.
`27`'s caveat, which said "25,348 of 32,218 indexed returns are not yet
downloaded", is corrected and the manifest regenerated.

### Gates

`518`: **lobbying READY, 35 tables** (was 33; the two Schedule C tables joined).
`87`: `ship_tables_shipping` 197 → **227**, `tables_missing_notes_contract`
24 → 22, ship rate 88.133% → 88.307%.
`293`: exit 1, 166 unwaived instances, **0 of them in 1091** (grepped).
`62`: exit 1. **None of its regressions name a lobbying table or any file this
pass wrote.** Naming the owners with the measurement, per standing rule 15:

| line | owner, measured |
|---|---|
| `files_with_columns_lost_vs_backup = 3` | `native_fi_roster.csv` 23→22 lost `in_cicd_nafi_map` and `cedar_entity_spine.csv` 44→43 lost `cicd_verified`, both vs `.bak_2026-09-02_pre844` — **script 844's owner**. `prime_contracts.csv` 75→70 lost the five `identifier_ruling_*` columns vs `.bak_2026-09-02_pre_1085_prime_psc_desc_repull` — **script 1085's owner, whose puller is live in this machine's process list right now** |
| `lint_*` ROSE 146 → 166 | 293 names each instance; the largest movers are `class2c` (+9) and `class4` (+5) across `1030`, `1031`, `1060`, `1104`, `980`, `992`, `846`, `852`, `873`. **Zero in 1091** |
| `rulings_unapplied` 1,215 → 2,894 | the rulings/adjudication workstream |
| `ship_tables_at_zero`, `tables_missing_from_25_TABLES`, `tables_missing_from_27_SPEC`, `tables_undocumented_in_codebook` | all four move together as tables enter `data/clean` ahead of `25`'s curated override list. **The integrator owns `25`.** My own contribution moved the opposite way: `nonprofit_schedule_c_lobbying.csv` left the biggest-unshipped list when `87` gave it a notes contract at 29,149 rows |
| `SHIPPING LOST: advocacy_passthrough_2026-08-07.csv` | already recorded in this file as a duplicate vintage ruled into `INTERNAL_TABLES` |
| `hearing_bill_links.csv` 465→464, `native_bills_subject_sweep.csv` 2,414→2,409 | the bills/votes workstream |

### Two stale things found in passing, not fixed, owners named

* **`86_build_series_breaks.py` re-measures its own subawards figures on every
  run and printed: `pre-FSRS count moved from 47 to 51`, FY2009 30→33, FY2010
  113→141, FY2011 1,652→1,953, FY2012 2,679→3,106.** The prose in that break
  row still quotes the old counts. **Subawards workstream.**
* **`docs/MONEY_TOTALLING_RULES.md` carries two `<!-- BEGIN FAADS -->` markers
  and one `<!-- END FAADS -->`.** Two blocks sharing a marker name are one
  block to `574`'s preserver (AGENT_FIELD_GUIDE §2). **FAADS workstream.**


---

## 2026-09-02 — workstream STANDARD: the punch list's own claims, the codebook fragment system, and rule 17

Full write-up: `docs/ARCHITECTURE_DECISIONS.md` **ADR-023-STANDARD-GUARD**.
Reader-facing warning: `docs/KNOWN_ISSUES.md` **STANDARD-PUNCHLIST-GUARD**.

### The finding that mattered most

`docs/datasets/_PUNCHLIST.md` is an INSTRUCTION SET — ten agents act on it —
and **43 of 65 "always empty column" claims on the 13 capped tables are FALSE**.
`526.scan()` stops at 20,000 rows and then asserts on that prefix.
`prime_contracts.csv` carries the line *"drop 10 always-empty column(s)"*; all
ten hold data, including `contract_transaction_unique_key` at **841,002**
non-blank of 1,217,768 and `naics_code` at **838,229**. Doing what the line says
would delete the contracting table's award keys and its NAICS.

Corroborated independently: the promotion workstream documented
`contract_award_unique_key` at **69.1%** filled and `naics_code` at **68.8%** in
`codebook_master.csv` the same day — the exact columns 526 called empty.

New guard, `code/1107_punchlist_claim_verify.py` (`verify` exits 1, `selftest`
proves it fires both directions). `526` is integrator-owned, so it was NOT
edited; the four-point patch is at the foot of
`docs/datasets/_PUNCHLIST_CLAIM_AUDIT.md`. **`526 verify` also returns 0
unconditionally today, so it is not a gate.**

### A closed loop nobody could have escaped

No `C11 … write codebook entries` punch item could close, whatever an agent did.
The sanctioned path (392, 208) is: write a fragment, then
`cedar_codebook.py build`. `build` was REFUSING — 14 rows sat in
`codebook_master.csv` that no fragment carried — so the file 526 measures could
not be rebuilt from the file the agent was told to write. Repaired by
`code/1108_codebook_fragment_repair.py repair`.

**It recurs.** 47 more rows were written straight to the master by five other
blocks (`02m_native_owned_businesses`, `05e_identifier_ledger`,
`05p_entity_relationships`, `06_nonprofit/np_orgs`, `18a_nest_enterprises`)
while this pass was running. That is the lost-update race `cedar_codebook.py`
exists to end. **Write the fragment, never the master, then run
`py -3 code/cedar_codebook.py build`** — and run `1108 repair` first if it
refuses.

### A licensing control that measured the wrong thing

`62`'s `duns_marked_publishable` reads `access_tier` and never `published`, and
it greps the variable NAME for "duns". Two rows walked through it:
`07_gaming/casino_city_id` at `published=1, access_tier=public`, and
`03_federal_funding/recipient_duns` at `published=1, access_tier=internal` — a
row that contradicts itself. Both now `0/internal`. `dist/` was never affected
(it already withheld the column); the CODEBOOK was wrong, and that is what a
buyer reads. **Suggested to the integrator: widen 62's metric to
`cedar_codebook.is_licensed_col` and score both fields.**

### 62, standing rule 15 — one line was mine, and it is closed

`regenerate_new_unsafe_writers = 1` was **this pass's own new script**: 845
flagged `1107` as a wholesale markdown writer minutes after it landed, which is
the gate working. Settled the honest way —
`845 regen docs/datasets/_PUNCHLIST_CLAIM_AUDIT.md`: generator exit 0, 1 removed
/ 1 added, 0 unpaired, the moved line being the open-item count 334 → 333.
Recorded in `MD_PROVEN_SAFE` with that result. **`845 verify` is green: 3 unsafe
writers, 0 new since baseline, floor re-recorded 9 → 3 while GREEN.**

Sharpening one attribution the entry above this one made generically:
**`tables_undocumented_in_codebook` 3 → 21 is 18 tables created TODAY**, none of
them this pass's — `geo_award_county_crosswalk`, `geo_place_county_crosswalk`,
`geo_county_dim`, `geo_county_two_sums`, `geo_aiannh_dim`,
`geo_aiannh_county_observed`, `geo_point_aiannh_assignment` (ADR-015 geography),
`cedar_constellation_edges`, `cedar_constellation_refusals`,
`cedar_entity_freshness`, `entity_dated_public_facts`,
`native_business_contract_links`, `native_business_contracting_by_nation`,
`native_business_identifier_crosswalk`, `sec_gaming_financial_disclosures`,
`sec_gaming_management_contract_terms`, `gaming_web_harvest_observations`,
`gaming_web_harvest_coverage`. The 3 that were there before are
`consultation_agency_coverage.csv`, `gaming_property_locations.csv`,
`wa_machine_transfers.csv`. Each new table's own workstream owns its codebook
block; `codebook_variables` rose 4,614 → 5,444 in the same window, **+103 of
that from this pass**.

### Rule 17 writers fixed (all five lost `cedar_uid`, one root cause)

`77_build_nagpra_dataset.py` (`write_csv`), `511_sam_entity_hierarchy.py`
(`write_csv`), `110_build_harmonized_views.py` (class 3,
`list(prof[0].keys())`), and `221_probe_regulations_gov_comments.py` — two
sites. **221 needed the stricter form**: `_append_csv` appends, and a literal
header on an append does not merely delete a column, it lands every field past
the mismatch one column to the left. Its `_derive_append` uses the LIVE header
verbatim and RAISES if the literal names a column the file does not have,
because appending cannot add one.

### Two artefacts of my own detectors, both removed rather than waived

* `845`'s orphan-heading signal accused every heading carrying a computed count
  — `"## The " + str(len(rows)) + " entities, by class"` can never be a literal.
  `heading_reproducible` now splits on number runs and requires the fixed parts;
  three selftest cases hold the line, including *a hand-authored heading that
  merely contains a number must still fire*.
* `293` class 6 paired `1107` with `cedar_harvest_conservation.csv` and
  `codebook_master.csv` because its SELFTEST FIXTURE used those filenames beside
  a `csv.writer`. The fixtures were renamed rather than waived — 526 reads
  whatever the monkeypatched constant points at, so the live name was never
  needed. 293 is now silent on 1107.

---

# WORKSTREAM FR-DTLL, 2026-09-02 — the `federal-register` consultation surface: the NAGPRA overlap, the letters, and the event parse

Scope: deepen `federal-register`, which was already READY. Two new scripts,
**1089** and **1090**, both claimed atomically through `1050_preflight.py claim`.
`docs/ARCHITECTURE_DECISIONS.md` **ADR-023-FR-DTLL** carries the decisions and
the ownership table; this entry carries the numbers and the gate state.

## What moved

| | before | after |
|---|---:|---:|
| `consultation_events.csv` rows | 11,402 | **11,402** (0 added; +8 columns) |
| `event_start_date` non-blank | 93 | **190** |
| `location` non-blank | 60 | **103** |
| Dear Tribal Leader letters Cedar holds | **6** | **597** |
| tables in the `federal-register` collection | 22 | 23 (+1 internal) |
| `codebook_master.csv` rows | 5,351 | 5,415 (+37 `09c`, +27 `09d`) |

## The three measurements worth carrying forward

**1. "95.5% NAGPRA" is a ROW share and it was being read as a document share.**
10,920 of 11,402 rows (95.8%) name a document `nagpra_notices.csv` also ships —
but only **1,831 distinct notices**, against 6,792 in the NAGPRA dataset.
**4,961 NAGPRA notices are absent from `consultation_events.csv` entirely.** The
two tables are a 27.0% intersection built by two different extractions, not a
duplicate pair. And the intersection is a WINDOW: **0 of 1,882 notices from
1994–2010, 1,817 of 2,264 from 2011–2022, 14 of 2,646 from 2023–2026** —
because revised 43 CFR 10 (effective 2024-01-12) replaced the *"in consultation
with representatives of"* sentence `96`'s net keys on with a bulleted
Determinations list. **The net stops catching notices exactly as NAGPRA volume
triples.** All of it is now columns on the row plus codebook block
`09c_consultation_events`, not prose.

**2. A 406 was hiding a 27-year series.** `962` recorded `ihs.gov` as
`NOT_CHECKED` on an HTTP 406. Re-probed with the full navigation header set —
the header **shape**, per `docs/BLOCKED_SOURCE_BYPASS_2026-08-26.md`, not the UA
string — `https://www.ihs.gov/robots.txt` returns **200** and reads
`User-agent: * / Disallow:` (empty = allow all), and the sitemap enumerates
**27 year indexes** of Dear Tribal Leader Letters back to 2000. 597 letters:
**IHS 574, BIE 14, BIA 9**, 2000-01-10 to 2026-08-25, 0 with a date the
publisher did not state.

**3. `code/1050_preflight.py ondisk` was right again.** All 2,313 consultation
notice texts were already in `data/raw/external/consultation/fr_text/`. The
event date and place were a PARSE, not a fetch. Zero requests for task C.

## Two defects this workstream found in its OWN first pass — both the repo's signature shape

* **A `?page=N` sitemap loop that FAILS OPEN.** `bia.gov/sitemap.xml` is a
  Drupal `simple_sitemap` INDEX; `?page=3` … `?page=20` return **the index
  itself**, HTTP 200, two `<loc>`s each. The first pass reported *"2,412 URLs
  over 20 pages"* — a plausible number about something else — and made 18
  pointless requests. Same shape as FPDS `AGENCY_CODE:` in
  `docs/PULL_DISCIPLINE.md`. It now walks the index's own children and refuses
  any shard that hands back an index.
* **An unanchored place regex that measured contact addresses.** Filling
  `location` from any `City, State` near a date put **657** museum contact
  addresses and excavation counties onto NAGPRA rows — *"Cambridge, MA"* out of
  *"should contact Patricia Capone, Peabody Museum"*, *"Coconino County, AZ"*
  out of where remains were removed in 1985. Both are places the notice prints;
  neither is a consultation location. A location is now read only from a notice
  that announces an event, and the fill fell **703 → 43**.

Also corrected: the first pass keyed IHS letters on a `DTLL` filename prefix and
dropped **462 of 836** PDFs, because pre-2010 letters are named
`12-14-2000_Letter.pdf` and `Anthrax Summary For IHS Clinicians.pdf`. The rule
is now the publisher's own `.../<year>_Letters/` folder. And the DTLL URL
pattern missed `bia.gov/service/progress-act/dtll` — the tenth URL `962`
counted — until it learned the abbreviation.

## GATE STATE AT THE CLOSE OF WORKSTREAM FR-DTLL — named, not stepped around

`py -3 code/62_no_regression_check.py` exits 1. Log `logs/1089_62b.log`.
**Nothing red is FR-DTLL's**, and here is the evidence rather than the
assertion.

- `py -3 code/293_lint_bug_classes.py` exits 1 and names 23 new instances.
  **`grep -E '(1089|1090)_'` over the full lint report returns nothing.**
- `files_with_columns_lost_vs_backup = 2` names `native_fi_roster.csv`
  (`in_cicd_nafi_map`) and `cedar_entity_spine.csv` (`cicd_verified`), both
  against `.bak_2026-09-02_pre844`. **Owner: whoever ran `844`.**
  `consultation_events.csv` is NOT among them — `1089` added eight columns and
  removed none, and `287_build_dependency_manifest.py` agrees.
- `regenerate_new_unsafe_writers = 1` is
  `1107_punchlist_claim_verify.py -> docs/datasets/_PUNCHLIST_CLAIM_AUDIT.md`.
- `contract_orphan_shippable = 7` is the same seven named in workstream
  INT-READY's entry above (three `.bak_` files registered as tables, plus four
  live-harvest tables). **Both FR-DTLL tables are owned**: `500.COLLECTIONS`
  `federal-register` now matches `dear_tribal_leader|dtll_`, verified by
  re-deriving the regex against both filenames.
- `tables_undocumented_in_codebook = 21`. **Neither FR-DTLL table is one of
  them** — `cedar_codebook.registered_tables()` returns
  `dear_tribal_leader_letters.csv` as SHIPPABLE and lists neither it nor
  `dtll_source_coverage.csv` as undocumented. `tables_missing_codebook_block`
  fell 21 → 19 across the two runs, which is these two blocks landing.
- The remaining lines — `rulings_unapplied` 2,894, `SHIPPING LOST:
  advocacy_passthrough_2026-08-07.csv`, `hearing_bill_links.csv` 465→464,
  `native_bills_subject_sweep.csv` 2,414→2,409, and the
  `tables_missing_from_25/27` family — are the advocacy, legislation and
  registry-lag lines already named in the INT-READY entry above. Unchanged by
  this workstream.

### One line that IS ours, and is deliberately left for the integrator

`dear_tribal_leader_letters.csv (807 rows)` appears under **NEW TABLES AT A 0%
SHIP RATIO**. It is documented and owned; it is simply not in `dist/` yet,
because that needs `87 -> 25 -> 27` per `docs/SHIPPING_RUNBOOK.md`. **It was not
run.** Fourteen other new tables from four other workstreams sit in the same
state in the same list, `25_build_publication_layer.py` rewrites the whole
publication layer, and six other agents were writing `data/clean` at the time —
shipping now would ship their half-finished tables too. Named here so the next
runbook pass picks it up rather than rediscovering it.

### `512_build_dataset_contracts.py` could not be run to completion, and why

Two attempts, neither of which produced a contract state. The first died on
`PermissionError: data\clean\subawards.csv` — another agent holding the file
open. The second produced no output in 50 minutes and was killed still running,
against **six concurrent copies of `512` and seven of `62`** started by other
agents; six copies of `512` were still live after it died, so a third attempt
would have added load to the contention rather than measured through it. Rather than report
an unmeasured contract state as green, the two new grain declarations were
validated directly against the live files with `512`'s own `GRAIN` dict
imported:

```
dear_tribal_leader_letters.csv  letter_id    807 distinct / 807 rows, 0 blank, 0 literal dups  -> VALIDATES
dtll_source_coverage.csv        coverage_id   35 distinct /  35 rows, 0 blank, 0 literal dups  -> VALIDATES
consultation_events.csv         (consultation_event_id, participant_name_as_published)
                                             11,402 distinct / 11,402 rows, 0 literal dups     -> STILL VALIDATES after +8 columns
```

**`512`'s own run is therefore UNMEASURED for this pass, and that is stated
rather than assumed green.** The declarations live in `GRAIN_FR_DTLL`, a new
per-workstream dict; no other workstream's dict was touched.

### The remaining DTLL surface, sized against what it was measured with

| host | status | measured |
|---|---|---|
| `ihs.gov` | ENUMERATED_IN_FULL | 27 of 27 year indexes walked; 574 letters. The 13 `urbanleaderletters` year indexes are a DIFFERENT series and were not harvested. |
| `bie.edu` | REPORTED_FLOOR | 1 of 1 sitemap shard; 14 DTLL URLs, 14 letters. |
| `bia.gov` | REPORTED_FLOOR | 2 of 2 shards, 2,412 URLs, 10 DTLL URLs → 9 letters + 1 publisher index page that itself links **2 further letter PDFs not yet promoted**. |
| `doi.gov` | REPORTED_FLOOR_PARTIAL_INDEX | 4 of 9 shards, 0 hits. **UNMEASURED beyond those four.** |
| `epa.gov` | REPORTED_FLOOR_PARTIAL_INDEX | 6 of 38 shards, 0 hits. |
| `usda.gov` | REPORTED_FLOOR_PARTIAL_INDEX | 6 of 8 shards, 0 hits. |
| `ed.gov` | REPORTED_FLOOR_PARTIAL_INDEX | **0 of 2 shards.** `ed.gov/sitemap.xml` is an index whose children point at `http://vpvmwevapp001-lkg.azurewebsites.net/` — a private Azure hostname leaked into a public sitemap — which 403s. A publisher defect, not a refusal of Cedar. |
| `hhs.gov` | NOT_CHECKED | `/sitemap.xml` HTTP **403**, and robots.txt names no `Sitemap:` directive to fall back to. |
| `hud.gov` | NOT_CHECKED | `/sitemap.xml` HTTP **404**. robots.txt is `User-agent: * / Allow: /` — HUD is open — but see ADR-023 on its Cloudflare `Content-Signal: ai-train=no`. |

**No row in `dtll_source_coverage.csv` says an agency does not publish Dear
Tribal Leader letters.** The strongest statement any of them makes is
`NOT_IN_PUBLISHED_INDEX`, which is a fact about a sitemap walked in full, and
`INV-DTLL-ABSENCE` fails the build if that status appears on a non-200 or a
partly-walked index. 89 requests across 10 hosts on the first pass, 17 on the
last (the rest served from the on-disk cache).

### RESTORED: 34 of 39 lines of the FAADS block in `docs/MONEY_TOTALLING_RULES.md`

The entry above this one flagged *"two `<!-- BEGIN FAADS -->` markers and one
`<!-- END FAADS -->`"*. Measured with a LINE-ANCHORED match, the live state was
worse: **one BEGIN, zero END, and the body cut to 5 lines from 39.** Everything
after *"so it survives.\*\*"* was gone — the FY2007 seam table, the stacking
rule, and the sentence that prevents a **$2,165,856,969 double count** across
the two faads tables.

Traced by counting the block in every revision of the file:

    83c7f00  39 lines, correctly closed
    257b597   5 lines, END marker gone   <- lost here
    ada1845   5
    2b70db8   5  (HEAD)

Restored **verbatim** from `83c7f00` — nothing authored, nothing edited, backup
at `.bak_2026-09-02_pre_1107_faads_marker_restore`. Every marker in the file is
now paired: 17 blocks, 0 unbalanced. **This was urgent for eight other
workstreams, not just FAADS**: with no END, `574`'s preserver sees the FAADS
block running to end of file, so `LOBBY-SUPERSESSION`, `SEC-GAMING`,
`NEWSLETTERS`, `GAMING-DEEP`, `DEALS-MERGE-1088` and
`DEEPEN-SUBAWARD-DENOMINATOR` were all inside it.

**FAADS workstream: please confirm the restored text is current** — it is the
2026-09-01 version and any measurement taken since needs re-applying INSIDE the
markers.

One method note, because I nearly published the wrong number. My first marker
audit used an unanchored regex and reported `ARCHITECTURE_DECISIONS.md` as
carrying three unbalanced markers. It does not — the regex was matching markers
QUOTED INSIDE PROSE, including the ones in my own ADR. Anchoring to line start
gives the true answer: that file is balanced and only `MONEY_TOTALLING_RULES.md`
was broken. A marker audit must anchor, or it counts the documentation of
markers as markers.


---

## 2026-09-02 — workstream QUARANTINE (1079): CDR-11 / CDR-12 closed, and the 62 gate is RED with nothing of mine in it

**What was done.** `code/1079_quarantine_method_exposure.py`, ADR-019, full
write-up `docs/QUARANTINE_EXPOSURE_LOG_2026-09-02.md`. Five columns carrying
the identity ledger's RULING onto `prime_contracts.csv`; 737 identifiers
withdrawn ($16,997,581,754.88 across 103,171 rows); 67 repointed
($2,443,371,845.81 across 6,550 rows); 126 entities moved; total obligations
unchanged to the cent. `verify` PASS on all seven invariants, `selftest` PASS
including the gate itself made to exit 1 three ways.

**`62_no_regression_check.py` exits 1, and standing rule 15 says name the owner
with a measurement rather than record it as "not mine" and continue.** Measured
2026-09-02 with twelve other agent python processes live in this repo:

| red line | owner, measured |
|---|---|
| `lint_class2c` 60 → 69 | nine NEW drop counters, named by 293: `1060_splink_pilot`, `1085`, `1086`, `846`, `852`, `873`, `104`, `106`, `107b`. **None is 1079** |
| `lint_class3` 0 → 2 | `1060_splink_pilot.py`, `992_newsletter_deal_candidates.py` |
| `lint_class4` 9 → 14 | `1030`, `1031`, `1110`, `980`, `992` — run-deadline patterns |
| `lint_class7` 42 → 44 | `1030`, `1031`, `1110` — positional candidate ids |
| `lint_class1` 0 → 1 | `1011_cross_dataset_reconciliation.py:430`, the additions glob |
| `rulings_unapplied` 1,215 → 2,894 | measured off `cedar_ruling_ledger_consolidated.csv`, producer `173_consolidate_rulings_ledger.py`. 1079 does not write that file |
| `contract_violations` = 11 | 4 are `federal_funding_transactions.csv` / `federal_funding_tribe_year_panel.csv` declaring a `tribe_id` that 843 removed; 7 are ORPHAN shippable `.bak_*.csv` files other passes left in `data/clean` |
| `tables_*` 5 metrics rising, `ship_tables_at_zero` 13 → 21 | 19 NEW tables from the geo, constellation, gaming-harvest and business-crosswalk passes, none of them mine |
| `SHIPPING LOST: advocacy_passthrough_2026-08-07.csv` | the table is gone from `data/clean`; not touched by this pass |

**One line DID name my columns and it is a mid-flight read, not a loss.**
`COLUMN LOSS ... prime_contracts.csv 75 -> 70 ... lost: identifier_ruling_*`.
The live file carries **75** columns and 227,540 rows flagged
`identifier_ruling_quarantined = 'Y'`; the gate was started while this pass's
`.part` had not yet been renamed into place, so it read the 70-column
pre-state. Re-measured after the rename: live 75, the `pre_1085` backup 75, and
`product_or_service_code_description` filled on 247,987 rows in **both** —
so agent 1085's repull was not lost either.

**A real cross-agent hazard this pass created and then measured away.** To
re-run the classifier from a clean pre-state, `1079` was rolled back by
restoring six tables from its own `.bak_<TAG>` copies. That restore reverts
anything another agent wrote to those tables in the window — the script-163
incident in miniature. It was done from a **literal list of six files, never a
glob**, and the one table another agent had touched in the window
(`prime_contracts.csv`, by `1085`) was checked column-by-column afterwards and
had lost nothing. The rule stands anyway: **restoring your own backup in a
repo with twelve live agents is a write to every other agent's table too.**

**And the reason a rollback was needed at all, which is the more useful
lesson:** `mode(awardee_name)` in duckdb has no defined tie-break, so
`MGKFVCKA3D73` came back as `MUSKOGEE TECHNOLOGY JOINT VENTURE` on one run and
without the words `JOINT VENTURE` on the next. The fragment rule exempts joint
ventures, so the same identifier was WITHDRAWN in one run and HELD in the next
— 8 rows and $500,078 that reconciled against nothing. Defect class 7. Fixed
with `first(nm ORDER BY c DESC, nm)`, and the joint-venture test now reads
every name the registrant ever filed.

**ADDENDUM 09:20 — `code/62_no_regression_check.py` IS BROKEN AND IT IS NOT
MINE.** It now dies before printing anything:

```
File "code/62_no_regression_check.py", line 1996, in main
    _live = (ROOT / "data" / "clean" / f).exists()
NameError: name 'ROOT' is not defined
```

The integrator owns 62 and no agent may edit it, so this is reported, not
fixed. **The standing gate is down for every workstream, not just this one**,
and a red gate nobody can run is worse than a red gate. Its last complete run
(09:0x, output preserved at the path named in the QUARANTINE section above)
exited 1 on 14 regressions, all traced to other workstreams.

**ADDENDUM 11:0x — a second cross-agent event, and the gate caught it.** After
this pass finished, an enricher landed on `prime_contracts.csv` at 10:57
(1,461,714,396 -> 1,462,947,197 bytes, same 75 columns, same 1,217,768 rows).
`1079 verify` re-ran and all seven invariants still held — attributed dollars
had fallen by exactly this pass's $16,997,581,754.88 and not a cent more — so
the write touched no attribution. **That is what a gate re-deriving both sides
buys: it can tell a neighbour's edit from a regression.** The Copper River
extension below was therefore applied with `CEDAR_1079_REDO=1`, which
re-processes each table from its CURRENT state instead of restoring it, so the
10:57 work was preserved rather than reverted. **Restoring your own backup is a
write to every other agent's table; re-processing in place is not.**


---

## 2026-09-02 — GATE 62 IS RED. Workstream `ACQUIRE-1119-1121` attributing every line, per standing rule 15.

*Standing rule 15 says: do not record a red gate as "pre-existing, not mine"
and continue; if it is genuinely another agent's, **name it and its owner
here** before moving on. This is that entry. Every attribution below is a
measurement, not a judgement, and the command that reproduces it is given.*

**What this workstream did:** acquired the eight ACQUIRE sources from
`docs/SOURCE_EXPLORATION_2026-09-02.md`. 12 new tables, 323,134 rows, from
`biamaps.geoplatform.gov`, `opendata.usac.org` and
`npiregistry.cms.hhs.gov`. Scripts `1119`, `1120`, `1121`, `1124` and the new
shared client `code/cedar_arcgis.py`. Full account:
`docs/BIAMAPS_ACQUISITION_LOG_2026-09-02.md`. Model decision: **ADR-028**.
Nothing committed.

### MINE, and closed before this entry was written

| ratchet | state | evidence |
|---|---|---|
| `tables_undocumented_in_codebook` | **all 12 of my tables are registered** | `py -3 code/1124_register_acquire_codebooks.py verify` — 49 checks, 0 failed. Every column of all 12 has a non-empty description and a `pct_filled` re-measured against the live file to 0.1pp. |
| `contract_grain_unstated_shippable` | **all 12 declare and VALIDATE a grain** | `py -3 code/512_build_dataset_contracts.py` — all 12 appear under exactly one collection with a primary key that 512 confirmed unique and present in the header. Dict `GRAIN_ACQUIRE`; no other workstream's dict was touched. |
| `contract_orphan_shippable` | **none of the 8 orphans is mine** | 500's patterns extended with `usac_`, `bia_` and `nppes_`; the mineral table is deliberately named `resource_*` so `natural-resources` claims it and `^bia_` does not. Verified: each of the 12 matches exactly one collection regex. |
| `lint_bug_class_instances` and every `lint_classN` | **293 names no file of mine** | `py -3 code/293_lint_bug_classes.py | grep -E "1119|1120|1121|1124|cedar_arcgis"` returns nothing. |

### MINE IN PART, and it is the ship chain, which no agent runs

`tables_missing_from_25_TABLES` (179 → 230), `tables_missing_from_27_SPEC`
(194 → 237), `tables_missing_notes_contract` (14 → 41) and
`ship_tables_at_zero` (13 → 40).

**12 of each increase are my tables.** Measured: none of the twelve appears as
a literal in `code/25_build_publication_layer.py` or
`code/27_build_dataset_manifests.py`.

**They are not left there out of neglect.** 62's own text on these four says
*"This is not the shipping gate — see `tables_undocumented_in_codebook` for
that"*, and its scan line this run reads **`25 TABLES derives from the
codebook: YES`** — so the twelve are reachable through the registry `1124`
just wrote. Adding them to the curated override lists and running
`87 → 25 → 27` is the ship chain, and `docs/ARCHITECTURE_DECISIONS.md` says
in three consecutive ownership tables that **no agent runs it**.
**INTEGRATOR ACTION**, with the codebook work already done.

### NOT MINE — named, with the owner

**`tables_undocumented_in_codebook` 3 → 26.** All 26 enumerated by
`CB.registered_tables()`; **not one is a table this workstream created.**
Reproduce: `py -3 -c "import importlib.util;..."` — or read the list in the
62 output. Grouped by the workstream that appears to own them:

| tables | apparent owner |
|---|---|
| `cedar_corroboration_census/_conservation/_disagreements/_observations`, `cedar_fact_corroboration` (5) | the corroboration workstream — `code/1118_corroboration_layer.py` |
| `cedar_constellation_edges`, `cedar_constellation_refusals` (2) | `851`/`852` constellation edges |
| `geo_aiannh_county_observed`, `geo_aiannh_dim`, `geo_award_county_crosswalk` (1,050,968 rows), `geo_county_dim`, `geo_county_two_sums`, `geo_place_county_crosswalk`, `geo_point_aiannh_assignment` (7) | the geo crosswalk workstream — `870_build_geo_crosswalks.py`, `873_build_aiannh_crosswalk.py` |
| `cedar_harvest_coverage_evidence`, `cedar_harvest_coverage_matrix` (2) | `1112_harvest_coverage_matrix.py` |
| `native_business_contract_links`, `native_business_contracting_by_nation`, `native_business_identifier_crosswalk` (3) | the Native-business crosswalk — `1000`/`1001` |
| `gaming_web_harvest_coverage`, `gaming_web_harvest_observations`, `gaming_property_locations` (3) | the gaming web harvest — `980` |
| `entity_dated_public_facts`, `cedar_entity_freshness` (2) | the stale-tail workstream — `1081`, `830` |
| `consultation_agency_coverage`, `wa_machine_transfers` (2) | consultation / WA gaming |

**`contract_violations = 12` and `contract_orphan_shippable = 8`.** All named
in `docs/schema/dataset_contracts.json`; **none is mine.** They are the
`tribe_id` columns dropped by `843_retire_cicd_scheme.py` and still named in
three declarations, a `federal_funding_tribe_year_panel` primary key that is
not unique (5,480 duplicates of 5,496), a `cedar_uid` named on a deals
additions table that has no such column, and **five `.bak_*` files registered
in the codebook as if they were tables** — `native_owned_businesses.bak_…`
×2, `prime_contracts.bak_…` ×2. A backup registered as a shippable table is a
registration bug, not a data one.

**`lint_class1` 0→1, `class2c` 60→69, `class3` 0→2, `class4` 9→14,
`class5` 6→7, `class7` 42→44** (total 146→163). 293 names the file for each
and **none of the 17 new instances is in a file this workstream wrote.** They
sit in `1060`, `1085`, `1086`, `1114`, `1115`, `846`, `852`, `873`, `992`,
`1030`, `1031`, `1077`, `518`, `870`, `980`.

**`rulings_unapplied` 1,215 → 2,894** and **`tier_A_ruled` 1,676 → 1,669.**
This workstream applied no ruling, wrote no assertion, ran neither `510` nor
`124`, and did not touch `cedar_identifier_ledger*`. Owner: the
ruling-propagation workstream (`1116`, ADR-026).

**`SHIPPING LOST: advocacy_passthrough_2026-08-07.csv`**, and
`hearing_bill_links.csv` 465→464 and `native_bills_subject_sweep.csv`
2,414→2,409. Nothing in this pass reads or writes any of the three.

### The one thing worth carrying forward from this

Nine of the twelve red ratchets are the **same event**: several workstreams
landed new tables on the same day, and the gate reports each new table as
several separate regressions across `codebook`, `25`, `27`, `notes` and
`ship_tables_at_zero`. **A day of acquisition therefore reads as a day of
regression**, and the honest reading of this run is "the warehouse grew, the
shelf did not" — which is exactly what 62 itself prints under READ THESE:
*"ship_ratio_pct fell 99.692% → 85.136% and shipped rows did NOT fall
(8,461,252 → 8,612,513)."*

That is a true and useful thing for the gate to say. It is also why the
codebook registry is the metric to act on and the other four are downstream
of it: registering a block is an agent's job, and the ship chain is the
integrator's.

---

## 2026-09-02 — `62` IS RED AND NONE OF IT IS THE CAPABILITY-STATEMENT PASS. Named, per standing rule 15.

*Workstream CAPABILITY-1114 (`code/1114_capability_statement_harvest.py`).
Build log `docs/CAPABILITY_STATEMENT_HARVEST_2026-09-02.md`, ADR-027.*

`py -3 code/62_no_regression_check.py` exits 1. Standing rule 15 forbids
recording that as "pre-existing, not mine" and walking on, so here is the
measurement and the owner of each line. **`1114` contributes nothing to any of
them**, and the evidence is that it is possible to say so precisely rather than
by assertion:

* **`code_duplicate_numbers` = 43, at the floor.** `1050_preflight.py claim`
  allocated `1114` strictly above the frontier; `ls code/1114_*` returns exactly
  one file. (Preflight reported **44** at the start of this session — above the
  floor and already failing `62` before this pass wrote a line. It is back at 43,
  cleared by whoever owned it.)
* **`lint_bug_class_instances` 146 → 170**, and the class rises under it
  (`class1` 0→1, `class2c` 60→72, `class3` 0→2, `class4` 9→14, `class7` 42→49).
  `293` names every new instance by file. They are:
  `1011_cross_dataset_reconciliation.py` (class1) ·
  `1060_splink_pilot.py` (class2c ×2, class3) ·
  `1085_prime_psc_desc_repull.py` · `1086_faads_award_key_promote.py` ·
  `1125_np_website_native_check.py` (×2) · `1129_place_ids.py` ·
  `846_session_audit.py` · `852_extend_constellation_edges.py` ·
  `873_build_aiannh_crosswalk.py`.
  **`1114` appears once in `docs/lint_bug_classes.json` and it is in the WAIVED
  list** — one `class5` line, waived in place with the reason that `harvest`
  writes no log and `build` recomputes `run_summary.json` from the full on-disk
  spools rather than from a run's counters, so a second run cannot rewrite it to
  zero. `class5` went **down**, 7 → 6.
* **`regenerate_new_unsafe_writers`** names `1080_sec_gaming_facility_revenue.py`
  (`FIG_COLS`, `TERM_COLS`). Not this pass. `1114` derives every header as the
  union of the on-disk header and the rows being written (`derived_header`), the
  correct read-modify-write idiom under 845 class3.
* **`tier_A_ruled` 1,676 → 1,669**, `rulings_unapplied` 1,215 → 2,894,
  `contract_violations` = 13, `contract_orphan_shippable` = 8, the
  `ship_tables_*` / `tables_missing_*` family, and the three tables that stopped
  shipping (`advocacy_passthrough_2026-08-07.csv`, `hearing_bill_links.csv`,
  `native_bills_subject_sweep.csv`). **`1114` writes nothing in `data/clean/`,
  no ledger row, no ruling and no dist manifest entry.** Its entire output is
  `data/staging/capability_1114/`, one file in `review/`, one new doc, and two
  marked blocks. Nothing it wrote can move a shipping metric.

**What this pass owes the gate**, and it is paid: its own `verify` holds ten
invariants and exits 1 on breach, `selftest` proves six of them fire on a
synthetic violation and that a clean fixture exits 0, and **`verify` V7 fired on
the real run** — `www.tyonek.com` returned the same md5 eleven times through
eleven URL fragments. It was purged (187 document rows, 76 findings, all kept
with their reason in `purged_duplicate_documents.csv`), not waived by raising
the ceiling.

**Not re-baselined.** `--baseline` is a floor, not an acknowledgement button.


---

## 2026-09-02 — PLACE IDS (ADR-030, `code/1129_place_ids.py`): what this pass owns at the gate, and what it does not

**What it wrote.** `data/spine/cedar_place_id_register.csv` (new, append-only,
1,051 bindings), `data/clean/cedar_places.csv` (new, 997 rows, codebook block
`20a_cedar_places` registered so it does not sit undocumented), two review files,
one `GRAIN_PLACE` dict in `512`, one prefix in `cedar_ids.PREFIXES`, marked
blocks in `ARCHITECTURE_DECISIONS`, `KNOWN_ISSUES` and `OWNER_DECISION_QUEUE`,
and one additive column pair (`cedar_place_id`, `cedar_place_id_absent_reason`)
on **27 tables**. Row and money conservation is asserted inside the write on
every one: row count identical and every numeric column's sum identical to the
cent, before and after. No row was added, removed or repointed anywhere.

**What it FIXED that was already red.**

1. **`846_session_audit.py` carried nine 0x08 BACKSPACE bytes where `\b` was
   intended** — present in the committed blob, not a working-tree accident.
   `_denom`, the gate for the gaming denominator this whole pass rests on, was
   matching `\x08(CASINO|RESORT|…)\x08` and therefore matching nothing: it found
   **0 duplicate groups** and reported *"771 distinct properties — shape
   changed"*. Two other checks were blinded identically. **Repaired: 9 bytes.
   `_denom` now PASSES at 787 − 16 − 57 = 714.** Word-boundary and unbounded
   forms were compared on the live file and give identical results, so no
   adjudication changed. `846` went 24/27 → **26/27**.
2. **Three writers that this pass's own migration made unsafe** —
   `1080_sec_gaming_facility_revenue.py` (`FIG_COLS`, `TERM_COLS`) and
   `92_build_gaming_capacity_official.py` (`COLS`) — were flagged NEW by `845`
   the moment the column landed, and were fixed with the `carry_live_columns`
   repair `845` itself prescribes. **`845 verify`: 3 unsafe writers, 0 new since
   baseline.** Not re-baselined.

**`62` IS RED, AND THIS PASS IS NAMING WHAT IS NOT ITS OWN** — standing rule 15,
which forbids recording a failure as "pre-existing" and walking away.
Re-measured 2026-09-02 after this pass, with the owner of each line:

| red line | measured | whose |
|---|---|---|
| `lint_class1` 0→1, `class2c` 60→69, `class3` 0→2, `class4` 9→14, `class7` 42→44, `lint_bug_class_instances` 146→163 | **`py -3 code/293_lint_bug_classes.py` names ZERO instances in `1129_place_ids.py`** — grep for the filename returns nothing. The named new instances are in `1011`, `1060`, `1085`, `1086`, `1125`, `1030`, `1031` and others. | other passes tonight. `1129` had two of its own (a `id(p)` in-memory key, class 7; a `miss += 1` drop counter that did not name what it dropped, class 2c) and **both were fixed rather than waived** — the ordinal replaced the memory address, and every unmapped key is now printed and named. |
| `tables_undocumented_in_codebook` 3→27, `tables_missing_codebook_block` 3→27 | `1129`'s new table **is documented**: fragment `20a_cedar_places`, 19 of 19 columns described, and the metric fell 28→27 when it landed. The remaining 27 are other new tables and `.bak` files. | other passes; `62` globs `data/clean/*.csv`, so any new table raises this until its block is written. |
| `tables_missing_from_25_TABLES` 179→233, `from_27_SPEC` 194→240, `missing_notes_contract` 14→44, `ship_tables_at_zero` 13→43 | `cedar_places.csv` is at most **+1** on each. Closing them means running `87` → `25` → `27`. | **the integrator.** `ARCHITECTURE_DECISIONS` says in three ownership tables that no agent runs the ship chain, and this pass did not. |
| `rulings_unapplied` 1,215→2,894 | this pass applied no rulings and wrote no ruling ledger rows. | another pass. |
| `tier_A_ruled` FELL 1,676→1,669, `contract_violations` 13, `contract_orphan_shippable` 8, the two `F-DELAWARE-ALIAS` ledger rows, `SHIPPING LOST advocacy_passthrough`, `hearing_bill_links` 465→464, `native_bills_subject_sweep` 2,414→2,409 | `1129` touched no ledger, no spine row, no bills table and no `dist/` manifest. | other passes. |
| `846` `attribution_method holds only its controlled vocabulary` (CRITICAL) | on `prime_contracts.csv`, which this pass never opens for writing. | another pass. |

**One new rule this earned, and it is not in the field guide yet:** *a regex
literal is the one place in this repo where a defect is INVISIBLE IN A
TERMINAL.* `cat`, `Read` and most editors render `0x08` as nothing, so `846`'s
source read exactly as intended while matching no string that can exist, and the
check reported a clean, plausible, entirely fictional number for as long as it
has existed. **When a detector reports a suspiciously clean zero, run `cat -A`
on its pattern before you believe it.** That is the twenty-fifth instance of
this repo's signature defect and the first one where reading the code could not
have caught it.

**Not committed. Not re-baselined.**


---

## 2026-09-02 — NP-WEBSITE + GAMING-TOTAL (`code/1125`, `1126`, `1127`; ADR-031)

**What landed.** The nonprofits' own websites were read (JOB 1) and the annual
series with gaming in it was built (JOB 2).

- `review/np_website_native_check_2026-09-02.csv` — 697 `NATIVE_VERIFIED_STRICT`
  organisations, 167 pages actually read, 11 whose own words say they are
  Native, 35 whose own words name a different community. `1125 verify` exit 0,
  `selftest` 7/7. Build log: `docs/NP_WEBSITE_NATIVE_CHECK_2026-09-02.md`.
  **`np_orgs.csv` was not opened for writing.**
- `data/clean/annual_indian_country_money_series.csv` — 116 rows,
  (fiscal_year, series_id). `1126 verify` exit 0, `selftest` 9/9. Rules in
  `MONEY_TOTALLING_RULES.md` `GAMING-TOTAL`; build log
  `docs/ANNUAL_MONEY_SERIES_BUILD_LOG_2026-09-02.md`; grain `GRAIN_ANNUAL_TOTAL`
  in `512`; codebook fragment `05s_annual_indian_country_money_series`,
  registered shippable.
- `nonprofit_schedule_c_coverage.coverage_basis` no longer carries one constant
  string on all ten rows. Fixed at `code/99` (`schedc_coverage_basis()`),
  applied by `1127`, which imports 99's own function rather than copying it.
  `1127 verify` exit 0, `selftest` 3/3.

**One new totalling defect found, and it was in a published table.**
`nigc_regional_ggr.csv` grouped by `fiscal_year` alone **doubles FY2002, FY2007
and FY2016** — $29.213B / $52.160B / $62.600B against $14.497B / $26.016B /
$31.300B — because every NIGC report restates the prior year and those three
sit under two `region_system_version` values. The discriminator
(`figure_vintage`) was already in the file and nothing was reading it.
`1126 verify` V6 re-derives the naive sum every run and fails unless the fence
removes at least three overlap years, so the check can tell working from
unnecessary.

### The 62 gate, named honestly (standing rule 15)

`62` is RED and was red before this pass. What is ours:

| red line | ours? | measured |
|---|---|---|
| `tables_missing_from_25_TABLES` 179→233, `from_27_SPEC` 194→240, `missing_notes_contract` 14→44, `ship_tables_at_zero` 13→43 | **+1 each, ours** | `annual_indian_country_money_series.csv` is one new table in `data/clean`. The other ~53 are other passes'. `62`'s own text says these count the CURATED OVERRIDE list and are *"not the shipping gate"*. |
| `tables_undocumented_in_codebook`, `tables_missing_codebook_block` | **ours went DOWN** | both **28 → 26** when the `05s_` fragment landed. This is the metric that actually gates shipping and our table now passes it. |
| `lint_class1` 0→1, `class2c` 60→69, `class3` 0→2, `class4` 9→14, `class7` 42→44, `lint_bug_class_instances` 146→163 | **not ours** | `293` names **zero** findings in `1125`, `1126` or `1127` — measured from `docs/lint_bug_classes.json`. `1125` had two class-2c drop counters and **both were fixed, not waived**: `plan` now prints every organisation it refused and `fetch` prints every host that returned no readable page. |
| `rulings_unapplied` 1,215→2,894 | not ours | this pass applied no rulings and wrote no ledger row. |
| `tier_A_ruled` FELL 1,676→1,669, `contract_violations` 13, `contract_orphan_shippable` 8, `F-DELAWARE-ALIAS`, `SHIPPING LOST advocacy_passthrough`, `hearing_bill_links` 465→464, `native_bills_subject_sweep` 2,414→2,409 | not ours | no ledger, spine, bills table or `dist/` manifest was opened. |

**`code/1116 ... verify` went RED → GREEN in this pass.** It was failing on four
superseded literals in `docs/DEPENDENCY_MANIFEST.md:68` — a GENERATED file, so
the fix was at source in `cedar_pipeline.py`'s enricher-cost string (787 named
as a ROW count with the 714 property denominator beside it; 174 split into 113
evidenced / 58 unsupported / 3 not-collected), then `287` regenerated. Now
`no unanswered superseded literals` across 290 files, exit 0.

### Two things the next agent should not have to rediscover

**1. `1125` and `1129` found the same `846` 0x08 defect independently, hours
apart.** `1129` owns the repair and its `KNOWN_ISSUES` block says so.
`ESCAPE-COLLAPSE-1125` is the part that is NOT covered there: **seven other
live scripts carry the same corruption — 41 bytes, 16 lines — and none is
repaired.** `code/503_identity.py` is the worst of them: both the `\b` and the
`\1` backreference collapsed, so an identity normaliser is inert and would emit
a control byte if it ever matched.

**2. This environment collapses a doubled backslash on the way into a shell
heredoc, and it did so three times in one session** — in a repair script (the
"fix" replaced 0x08 with 0x08 and reported success), in a Python source patch
(a line-continuation backslash became a real newline and broke the file), and
in the first draft of the `KNOWN_ISSUES` entry describing the defect. Write
`bytes([0x5C, 0x62])`, or use an editor, and assert the remaining count.

**Not committed. Not re-baselined.**

---

# 2026-09-02 · LS · `1134` — the ledger's `state` column held 12,127 UEIs, and the fix for it was applied downstream of the defect

`code/1134_repair_ledger_state_uei_contamination.py` — `report` / `apply` /
`verify` / `selftest`. Number claimed atomically via `1050_preflight.py claim`.

## The measured state, before anything was written

| table | rows | `state` = this row's own `identifier` |
|---|---:|---:|
| `data/spine/cedar_identifier_ledger.csv` | 19,232 | **12,127** (63%) |
| `data/clean/cedar_publishable_identifiers.csv` | 1,577 | **699** |
| `data/clean/cedar_identifier_ledger_tiered.csv` | 19,232 | 0 |
| `data/clean/cedar_identifier_ledger_final.csv` | 20,577 | 0 |

All 12,127 are `identifier_type = UEI`, all from
`master_tribal_entity_registry.csv`, all 12,127 distinct identifiers. The
4,937 CAGE and 1,104 EIN rows were never affected.

## THE BRIEF SAID COLUMN SHIFT. THE SHIFT WIDTH IS ZERO.

Worth stating plainly, because the wrong diagnosis leads to the wrong repair: a
shift displaces every field past the insertion point, so a one-column fix would
have left the rest wrong. Measured three ways, all agreeing it is a
**single-cell overwrite**:

1. **v3 (broken) vs v6 (repaired), 11,392 rows matched 1:1 on (uei, name,
   tribe_id), all 26 columns.** Differences: `hq_state` 11,392, `hq_city`
   11,391 (**v3-blank**, filled later by the geocoder), `hq_zip` 909 (same),
   and 2 rows on six columns (an unrelated record correction). Every other
   column byte-identical. No debris, no hole.
2. **The raw registry, 13,191 rows x 12 columns.** Exactly ONE column ever
   equals the row's own UEI: `physical_state`, 12,127 times. Both neighbours
   (`verified_date`, `n_transactions_master_prime`) are 100% populated on the
   contaminated rows.
3. **The code.** `dissertation/.../sam_extracts/build_master_entity_registry.py`
   line 126: `physical_state=("recipient_location_state_code", "first") if
   "recipient_location_state_code" in prime.columns else ("awardee_uei",
   "first")`. `master prime file.dta` has no such column, so the else branch
   aggregated the UEI into the state field for every UEI in master prime. The
   1,064 rows that came by the hand-matched path never went through that
   groupby: 134 real states, 929 blanks.

**A silent column SUBSTITUTION is worse than a shift.** A shift is a parser bug
you fix once; a fallback that swaps in a different real column emits a full
column of plausible values, fails no check, and recurs on the next renamed
column upstream. Raised with the owner as `LS-1` in
`review/OWNER_DECISION_QUEUE.md` — it is his repo, and Cedar's guard does not
protect his own analyses. His attribution logic is NOT affected:
`cluster_v3_parent_brand.py:237` takes state from `recipient_state_code`
directly and its `geo_ok` gate was live throughout.

## THE $8.21B HYPOTHESIS WAS TESTED AND IS FALSE

Put to this pass as potentially the largest finding here: that the **15,878**
`ledger_uei_state_disagreement_withheld` rows in
`federal_funding_transactions.csv` — **$8,210,723,480.00**, 120 proposed
entities — were withheld against a corrupted state.

**0 of 15,878 rows. $0.00 of $8.21B.**

`115_pull_assistance_archive.py:892` builds its comparison state from
`cedar_entity_spine.csv`, keyed on `tribe_id`. It has never read the identifier
ledger's `state`. The spine's `state` is clean — 1,492 two-letter codes, 63
blanks, **zero UEIs** across 1,555 rows — and a blank yields `agree="unknown"`,
which cannot withhold. All 120 proposed entities carry a real two-letter spine
state. **98 of the 120 also have contaminated ledger rows**, which is precisely
why the coincidence reads as causal. Nothing was re-attributed; Santa Clara
County Housing Authority (CA) is still not Pueblo of Santa Clara (NM).

## THE DEFECT SAT UPSTREAM OF ITS OWN FIX

`71_fix_known_defects.py` defect 5 found this and repaired
`cedar_identifier_ledger_tiered.csv` and `cedar_identifier_ledger_final.csv`.
It never touched `data/spine/cedar_identifier_ledger.csv`, the file both are
BUILT FROM, and it never touched `cedar_publishable_identifiers.csv`, which
`03` writes from the same rows in the same pass. So every shipped copy measured
clean while the source measured 63% corrupt, and a rerun of `03` would have
pushed all 12,127 back in.

**Rule: when you repair a derived table, name and check the table it derives
from in the same pass.** A green check on a pipeline's output says nothing
about its input.

**And sweep the CLASS, not the instance.** The brief named one table. `62`'s
new rule-18 check looks at every CSV in `data/spine/` and `data/clean/` that
carries both an `identifier` and a `state` column — 5 tables — and that is the
only reason `cedar_publishable_identifiers.csv`, **1,577 rows, every one of
them tier A and publishable**, was found at all. Its other 878 rows held
unnormalised full state names, so not one row of the most customer-facing copy
of the ledger carried a usable state.

## THE REPAIR

Authority: `data/raw/external/need_v6_geocoded.csv` (v6, 18,110 rows, 0
contaminated), keyed on `enterprise_uei`. A state is written **only** where v6
gives exactly one two-letter value, and **BLANK** otherwise. Nothing is
inferred from a name, a ZIP or a sibling row.

| table | recovered | left BLANK | full names normalised | blanks filled from v6 |
|---|---:|---:|---:|---:|
| `cedar_identifier_ledger.csv` (spine) | **11,943** | **184** | 828 | 76 |
| `cedar_publishable_identifiers.csv` | **697** | **2** | 828 | 0 |
| `cedar_identifier_ledger_tiered.csv` | 0 | 0 | 0 | **12,019** |
| `cedar_identifier_ledger_final.csv` | 0 | 0 | 0 | **12,026** |

0 conflicts (no UEI for which v6 gives two states), 0 missing v6 rows.
`docs/LEDGER_STATE_REPAIR_1134.json` carries the summary, the per-table
disposition counts and the 184 identifiers left blank BY NAME;
`review/ledger_state_repair_1134_cells.csv` (git-ignored, 2.8 MB) carries all
38,603 individual cell dispositions. Both are derived from the `.bak` rather
than from the run's counters — the first version
wrote counters, and the idempotent rerun of the script that made the manifest
overwrote it with zeroes.

**BLANKING IS NOT REPAIRING.** 71 blanked what it rejected. v6 held the true
state for **12,019 of 14,923** blank rows in the tiered ledger and **12,026 of
16,250** in the final one. A shipped column reading "unknown" where the
authority says "VA" is the first defect in different clothes.

**48 multi-state strings (`Alabama; Texas`) and 3 junk values (`BRUNEI &
MUARA`, `-`) were LEFT EXACTLY AS THEY ARE**, not blanked. Blanking deletes
evidence with nothing to recover it from. Flag, never delete.

## `verify` FAILS WHEN THE WORK HAS NOT LANDED, AND THAT IS PROVEN

Four invariants: I1 absence, **I2 presence**, I3 honesty vs v6, I4 blast radius
against the `.bak`. I2 requires every row v6 can speak to to carry v6's answer
— so an untouched table scores 0 and fails, and **a table somebody merely
BLANKED also scores 0 and also fails**. `selftest` runs the real check against
a synthetic table in all three states and asserts the two failures and the one
pass; it also asserts I4 catches a change outside `state`. All four green.

I4 on the live run: spine 19,232 rows / 14 cols unchanged, **13,031 `state`
cells moved and nothing else**; tiered 19,232 / 22, 12,019 cells; final 20,577
/ 29, 12,026 cells; publishable 1,577 / 18, 1,527 cells.

## THE REGENERATE DEFECT — CLOSED, AND PROVED, NOT ASSERTED

* **`01_build_entity_spine.py`** already ran `clean_state` on the registry leg,
  and `LEDGER_REFRESH = ()` means `merge_table` cannot overwrite a repaired
  cell. Dry run AFTER the repair: `19,232 -> 19,358 rows (+126 new, 19,106
  matched, 0 lost), 14 -> 14 cols, 0 blanks filled, 0 refreshed`. **The repair
  survives a rebuild.**
* **`03_apply_exclusions_and_tier.py` had NO guard** and is the only route from
  the spine ledger into both clean tables. One added (`clean_state`, verdicts
  printed by NAME, not counted in silence). **Proved, not asserted: 500
  contaminated rows injected into a COPY of the spine ledger, `03` run against
  it with `CLEAN` / `SPINE` / `REVIEW` repointed at a temp dir — it printed
  `[0] state column guard - 500 REJECTED: held this row's own UEI`, and 0
  reached either output.** No live file was touched by that test.
* **`62_no_regression_check.py` rule 18**, `ledger_state_holds_own_identifier`,
  added to `MUST_BE_ZERO`. Currently **0**, across 5 tables carrying both
  columns.

## GATE 62 — what is mine and what is not

`ledger_state_holds_own_identifier = 0`. Every other failing line was already
failing and is already owned above in this journal:

| line | mine? | evidence |
|---|---|---|
| `tier_A_ruled` FELL 1,676 -> 1,669 | **no** | recomputed off my own `.bak`: **1,669 before AND 1,669 after**. Unchanged by this pass |
| `rulings_unapplied` 1,215 -> 2,894 | no | no ruling applied, no ruling-ledger row written |
| `contract_violations` 14, `ship_tables_at_zero` 13->44, the four `tables_*` lines, `SHIPPING LOST`, `hearing_bill_links`, `native_bills_subject_sweep` | no | no new table created, and no `dist/` manifest, bills table or codebook opened |
| `lint_*` ROSE | no | `293` names **zero** findings in `1134`. Its one hit on `03_apply_exclusions_and_tier.py` is class6 (`cedar_identifier_ledger_tiered.csv` has both a rebuild writer and an in-place enricher) and is **in the baseline** — `293`'s NEW-instance list names 1077, 30, 518, 870 and 99 for class6, not 03. class6 overall FELL 31 -> 27 |

`846_session_audit.py`: **27/27 pass, 0 fail.**

## One thing the next agent should not have to rediscover

**`docs/STATE_OF_THE_LAND.md` does not exist**, and a brief sent this pass to
read it. The root-level `STATE_OF_THE_LAND_2026-08-07.md` is the nearest thing
and carries its own superseded-numbers banner. The live orientation set is
`README.md` -> `START_HERE.md` -> `docs/AGENT_FIELD_GUIDE.md` -> this file.

## POSTSCRIPT — two more files carry it, and they are NOT live tables

A sweep of `dist/`, `data/staging/` and `review/` for the same shape found two
more, both dated 2026-08-05 review-queue snapshots and both still read by live
code (`1103`, `173`, `581`, `91`):

    review/review_queue_2026-08-05.csv                                   1,008
    review/_already_ruled_removals/..._already_ruled_2026-08-26.csv        739

**Deliberately not repaired.** They are dated snapshots of what the queue said
on a day, and the whole value of a snapshot is that it still says it. The
consumers use them for `identifier`, `tribe_id` and the ruling columns, not for
`state`. Rule-18 in `62` scopes to `data/spine/` and `data/clean/` — the live
tables — on purpose; widening it to `review/` would make every historical
artefact a gate failure.

**`dist/` is clean.** No shipped table carries both an `identifier` and a
`state` column with a contaminated row, so nothing reached a customer.

---

## A REGEX LITERAL IS THE ONE PLACE IN THIS CODEBASE WHERE A DEFECT IS INVISIBLE IN A TERMINAL (2026-09-02, ESCAPE-COLLAPSE-1125, `code/1136_control_byte_gate.py`)

**The rule, first, because it is the part that generalises.**

> **Before you believe a suspiciously clean zero out of a regex, look at the
> BYTES.** `cat -A`, `xxd`, or `py -3 code/1136_control_byte_gate.py report`.
> `cat`, `Read`, `git diff` and every editor in this environment render a
> `0x08` backspace as nothing or as a cursor move, so a pattern whose word
> boundary has collapsed into a control byte **reads on screen exactly as its
> author wrote it** while matching no string that can exist. It does not raise.
> It matches *less*, silently, and every count downstream of it looks like a
> measurement.
>
> This is the tenth instance of the repo's signature failure — *a check that
> does not measure its own name* — and it is the only one where reading the
> source carefully is not enough to find it.

**And the rule that stops you re-creating it:**

> **This environment collapses a doubled backslash on its way into a shell
> heredoc.** Never write a file containing a backslash with `cat <<EOF`. Use an
> editor tool, or a Python script that builds the bytes explicitly
> (`bytes([0x5C, 0x62])` for `\b`). Then **assert the remaining count is zero**
> rather than trusting your own "replaced N occurrences" line. A prior repair
> script authored as `.replace(bytes([8]), b'\\b')` arrived on disk as
> `b'\b'` — which Python reads back as 0x08 — so it replaced the byte with
> itself, reported success, and changed nothing. The same collapse ate a
> `KNOWN_ISSUES.md` draft and a line-continuation in a patched source file:
> three times in one session, in three file types.

### The sweep

Scanned `code/**/*.py`, `docs/**/*.md`, the root `*.md` and
`docs/schema/**/*.{json,txt}` — 975 files — for **every** control byte a regex
escape can collapse into: `0x00`–`0x08` (`\0`–`\8`, `\b`), `0x07` (`\a`),
`0x0b` (`\v`), `0x0c` (`\f`), `0x0e`–`0x1f`, `0x7f`. Tab, newline and carriage
return excluded.

**41 bytes, 7 files, 15 lines.** Every one is `0x08` except a single `0x01`,
and every one sits in a regex literal where a word boundary is the only
sensible reading. **No legitimate literal control byte exists anywhere in
scope** — no form-feed record splitter, no vertical-tab delimiter, nothing in a
data-parsing path — so every one of the 41 is a defect. The prior pass recorded
"41 bytes across 16 lines in 8 files"; the byte count reproduces exactly, the
line and file counts do not, and the eighth file was `846_session_audit.py`,
repaired separately by PLACE-IDS before this sweep ran.

### Repairing a dead pattern is a DATA correction wherever the output moves

Each site was run in **both** forms — the byte as it stood on disk, and the
repaired escape — against the corpus the script actually reads. Three moved
something. Four did not, and are repaired anyway, because a guard that cannot
fire is not a guard.

| site | corpus | broken → repaired |
|---|---|---|
| `503_identity.py:95` `clean()` | 18,506 names (spine, register, aliases, 9,098 distinct `recipient_name`) | **7 distinct names normalise differently.** The distinctive-token subset test — `resolve()`'s last resort — goes from NO MATCH to MATCH for two Native governments |
| `1080…:275` `PAT_B1` | 609 SEC filings, 1080's own `totext`/`flat`/alias alternation | **6 → 28 matches.** 22 new per-facility revenue figures, Mohegan Sun (11) + Mohegan Sun Pocono (10) + MGE Niagara (1), FY2018–21, $5,756,300,000 as printed |
| `1089…:254–5, 334–6` | all 2,313 FR consultation texts through the real `parse_notice()` | **7 documents move**, all place lists. **7 shipped `consultation_events.csv` rows carry a phantom street fragment as their `location`** |
| `1104…:363–4` `FURNITURE` | 51,579 `nagpra_notice_entity_bridge.csv` rows | **1 → 5.** The audit's own D1 check now FIRES: `01-8989` keys *"NAGPRA coordinator for the Walker River Paiute Tribe…"* to `TRBF-WLKRRV-00` |
| `142…:1024–5` | 1,749 cached pages, 2,519 metric candidates through real `has_counting_cue()` | **0 verdicts change** — `CUE_WORDS` already covers it |
| `76…:836` | all 366 shipped `federal_recognition_events.csv` rows through real `classify_mechanism()` | **0 mechanism labels change**; 6 rows get a better `mechanism_basis` |
| `561…:557–60` | 689 cached shard-K pages | **0 → 0** today, but 14 of 18 hijack markers were dead — a live-fetch guard whose value is in the next run |

**The two worst, stated plainly.**

**1. `503_identity.py` is the identity normaliser and it was inert.** One line
was `re.sub(r"<0x08>MC ([A-Z])", r"MC<0x01>", s)` — *both* the boundary and the
`\1` backreference collapsed, so it is the only site where the **replacement**
was corrupt too: had it ever matched it would have written a control byte into
an entity name. It never matched, so the 0x01 was latent, not live (measured:
the broken form emitted a control byte 0 times across 18,506 names). Repaired,
`clean("FT MC DOWELL YAVAPAI NATION")` and `clean("FORT MCDOWELL YAVAPAI
NATION")` fold to one key for the first time, and:

```
FILED "MC GRATH NATIVE VILLAGE COUNCIL"
   broken tokens {GRATH, MC}      vs spine AKNF-MCGRTH-00-…{MCGRATH}  -> no match
   fixed  tokens {MCGRATH}        vs spine AKNF-MCGRTH-00-…{MCGRATH}  -> MATCH
```

**151 rows / $11,358,100.32 of federal assistance to the McGrath Native Village
Council sit `attribution_status = unattributed` in the shipped
`federal_funding_transactions.csv` today**, and neither loose-path refusal
guard (G1 admin-geography, G2 civic form) refuses the name. *This is a
PROPOSAL, not an applied attribution* — a dollar-keying link is a ruling, and
`503` is a library, not the writer. It is in
`review/collapsed_escape_flagged_rows_2026-09-02.csv` and the owner queue.

**2. `1089`'s street-fragment refusal has never once fired**, and its own
docstring names the exact defect it was written to stop: *"2401 M Street, NW,
Washington, DC yields the phantom `NW, Washington`"*. With a collapsed boundary
`STREET_TOKEN` is `<0x08>(Avenue|Ave|Street|…)<0x08>`, which matches nothing, so
the guard was a no-op from the day it was written. Seven shipped rows carry the
result, and `location_basis` shows **four of them were written by 1089 itself**:

```
CONS-FR-2014-03720   'M Street NW., Washington'                 -> no place
CONS-FR-2016-10525   'E Street SW., Washington'                 -> no place
CONS-FR-2012-5438    drops 'West Dunlap Avenue Phoenix, AZ'
CONS-FR-2017-12494   drops 'Port Puget Sound Zone, WA'
CONS-FR-00-27437 / 2011-18096 / 2019-17786   (basis blank -> written by 96)
```

**The repair does not self-heal them.** `1089` fills `location` only when it is
blank, so re-running it leaves all seven exactly as they are. Flagged, never
deleted, no `cedar_uid` touched.

### The gate, because a repair with no gate regresses

```
py -3 code/1136_control_byte_gate.py report    # inventory, with cat -A rendering
py -3 code/1136_control_byte_gate.py apply     # repair the adjudicated manifest
py -3 code/1136_control_byte_gate.py verify    # EXIT 1 if any byte reappears
py -3 code/1136_control_byte_gate.py selftest  # 7 fixtures prove it FIRES
```

`apply` refuses any file whose byte census does not match the manifest exactly
— a changed census means the file moved and the adjudication no longer
describes it — backs up to `.bak_2026-09-02_pre_1136_control_byte_gate`, writes
through `.part`-then-rename, and **asserts zero remaining** rather than
trusting its own report. A byte that is genuinely meant to be there goes in
`ALLOWLIST` with a stated reason; nothing qualifies today.

**Wired in two places, both of which run every session:**

- **`293_lint_bug_classes.py` gained `class9`**, consumed from `1136.scan()`
  and never re-derived there — the same contract `class7` has with `284`,
  because two detectors for one class drift and a drifted detector is worse
  than none. `--selftest` runs 1136's seven fixtures. Note that class 9 is the
  one class `ast` cannot see: once the module parses, the byte is just a
  character inside a string constant.
- **`846_session_audit.py`** carries it as a CRITICAL claim. 846 is where this
  started — nine of these bytes in its own source blinded `_denom` into
  publishing "771 distinct properties" against a true 714.

Current state: **class9 = 0**, `1136 verify` PASS over 975 files, `293
--selftest` all green including class9.

### `62_no_regression_check.py` was RED when ESCAPE-COLLAPSE-1136 landed, and none of it is that workstream's. Named here per standing rule 15.

*Measured 2026-09-02, immediately after `1136 apply`. Recording it rather than
stepping around it, and naming an owner with a measurement rather than writing
"pre-existing, not mine".*

**What ESCAPE-COLLAPSE-1136 changed, in full:** 41 bytes inside regex literals
in 7 scripts, an additive `class9` detector in `293`, an additive claim in
`846`, `AGENTS.md`, `docs/KNOWN_ISSUES.md`, one new script
(`code/1136_control_byte_gate.py`) and one new review file. **It wrote no table
in `data/` and no file in `dist/`, and it ran no builder.** `git status` over
`data/` and `dist/` shows nothing from it. Its contribution to every lint
metric is **0** — `class9 = 0` on a clean tree.

| red metric | owner, with the evidence |
|---|---|
| `tier_A_ruled` FELL 1,676 → 1,669 | the ledger was rewritten twice in the last three hours by **`1122_ladder_repoints`** and **`1134_repair_ledger_state_uei_contamination`** — both `.bak_2026-09-02_pre_…` files sit beside `cedar_identifier_ledger_final.csv` |
| `rulings_unapplied` ROSE 1,215 → 2,894 · `corrections_not_propagated` ROSE 2 → 4 | same two ledger rewrites |
| `ship_tables_at_zero` 13 → 46 · `tables_missing_codebook_block` 3 → 27 · `tables_undocumented_in_codebook` 3 → 27 · `tables_missing_from_25_TABLES` 179 → 236 · `tables_missing_from_27_SPEC` 194 → 243 · `tables_missing_notes_contract` 14 → 47 | the **`1119`/`1120`/`1121` ACQUIRE wave** (`BIAMAPS_ACQUISITION_LOG_2026-09-02.md`, 358,336 rows) landed ~46 new clean tables without codebook blocks. `SHIPPING_RUNBOOK.md`: write the block, then `87 -> 25 -> 27` |
| `contract_orphan_shippable` = 11 · `contract_violations` = 16 | `docs/schema/dataset_contracts.json` and `docs/DATASET_CONTRACTS.md` are modified in the working tree by another pass |
| `SHIPPING LOST advocacy_passthrough_2026-08-07.csv` · `hearing_bill_links.csv` 465 → 464 · `native_bills_subject_sweep.csv` 2,414 → 2,409 | dist manifest, same shipping wave |
| `lint_bug_class_instances` 146 → 163 (`class1` +1, `class2c` +9, `class3` +2, `class4` +5, `class7` +2) | **every named site belongs to another script**: `1011`, `1060` (×3), `1085`, `1086`, `852`, `873`, `992`, `1030` (×2), `1031` (×2), `1111`, `980`, `1077`, `30`, `518`, `870`, `99`. The one that looks like this workstream's — `class2c 846_session_audit.py: fails += 1` — is **in `HEAD`**: running `293.detect_class2c` against `git show HEAD:code/846_session_audit.py` returns the same finding at line 565, and against the working tree at line 589. Only the line number moved. 293's baseline predates HEAD |

**`class9` is 0 and stays 0.** `1136 verify` PASSES over 976 files.
**No baseline was re-recorded.** `--baseline` is a floor, not an
acknowledgement button, and re-recording it here would have buried all of the
above.

---

## 2026-09-02 — workstream `CONSOLIDATE-PUBLICATION-RULES`: the safety rules had five copies, reconciled by regex, and two of the five were already broken

**`code/cedar_publication.py` is now the ONE copy of `NEVER`, `GATES`,
`FLAGSHIP`, `SPINE_TABLES`, `PRODUCT_ID`, `DROP_COLS`, `YEAR_COLS`, the shelf
sets and `row_ok()`.** 760, 770, 1135 and 1137 import it. Full reasoning and
the measurements: **ADR-035** in `docs/ARCHITECTURE_DECISIONS.md`.

**The standing rule this earns: never read a constant out of another script's
SOURCE TEXT.** Five scrapers did, all justified by the same false claim — *"a
module whose name begins with a digit is not importable, and 770 does file work
at import time."* Neither half is true. `importlib.util.spec_from_file_location`
imports `770_sample_extracts.py` in **0.04 s**, and every file read in it is
inside `main()`. **A regex over source text fails OPEN — `{}` or `None`, and
the caller decides. An import fails CLOSED, with a traceback naming the missing
symbol.**

Two of the five were already broken and nothing had noticed:

* **`1137._from()` failed open.** Its regex could not match the annotated
  binding `COLLECTIONS: list[dict] = [`, so `shelves()` returned `{}`, every
  collection failed the shelf test, and the build printed **"0 customer
  shelves" and exited 0**.
* **`770._760_product_id_map()` was never called.** It carried the comment *"so
  drift is a hard failure rather than two files quietly disagreeing"* and had
  no call site anywhere in the tree. **A gate that is defined and not invoked
  is not a gate** — grep for the call, not the definition.
* And `DROP_COLS` / `YEAR_COLS` were plain duplicated literals in 1135 **and**
  1137, with no scraper and nothing comparing them at all.

**A shared name has to say WHAT IT IS, and the new gate found the proof on its
first run.** 770 used the bare name `SPINE` for a *set of table names*; 1135 and
1137 both use `SPINE` for the `data/spine` *directory* `Path`. Three files, one
name, two unrelated types, kept apart only because none of them imported
another. The shared constant is `SPINE_TABLES`.

**760's spine scrape was a live hazard.** It ended `if j >= 0 else set()`, so
the day 770 stopped carrying a `SPINE = {` literal it would have silently
returned an EMPTY set and reported every spine-resident flagship as an
unclaimed table. That day was today.

### The brief this workstream was given had the site consumer BACKWARDS

It said *"`dist/samples/` is consumed by the SITE repo (PR #33 imports it)."*
Measured: the product repo's `scripts/import_cedar_manifest.py` reads
**`dist/review/MANIFEST.csv`** and **`dist/review/samples/<c>/<t>__10.csv`** —
`1135`'s output — plus `dist/collection_descriptors*.json` from 760 and 770's
`FLAGSHIP` **by text**. It never touches `dist/samples/`, which is 770's
separate curated fifteen-file product. **The half of 1135 the brief nominated
for retirement is the half with the live consumer.**

That importer is the ONE text-scraper that survives, and it cannot be fixed
from here: it lives on branch `claude/real-collections-manifest`, a tree
disjoint from `master` that never merges. So 770 keeps a `FLAGSHIP = {...}`
literal that is **generated** by `py -3 code/cedar_publication.py sync`,
`assert`ed equal at 770's import, and gated by `verify` under **both** external
scrapers' exact expressions.

### 1135's `full` half is NOT superseded by 1137 — measured, not assumed

| | |
|---|---:|
| tables 1135 publishes in full | 239 |
| 1137 flagship tables (13 datasets) | 13 |
| …also full-copied by 1135 | 12 |
| **tables 1135 ships in full that 1137 never ships** | **227** |
| `dist/review/spreadsheets` | 8.26 GB |
| …duplicating a 1137 flagship | 2.44 GB (29.6%) |
| …tables 1137 does not ship | 5.81 GB (70.4%) |

So **nothing was retired.** The `full` half has no consumer today (the site
importer sets `full_files.served = false` and declines to copy it), which makes
it a retirement candidate *on that ground* — but not on supersession, which is
false for 227 of 239 tables. The measurement and the conditions for retiring it
are written into `1135`'s docstring.

### Behaviour: proved, not asserted

Old and new code run against the same live tables in two shadow trees (`code/`
copied, `data/` `docs/` `review/` junctioned, `dist/` separate).
**315 of 316 output files byte-identical**, across 770's 16, 1135's 295 and
760's 2. The one difference is `dist/customer/MANIFEST.csv` and it is entirely
the CONCURRENT `gaming`-as-13th-dataset workstream: 12 common datasets, **0
cell differences outside the two columns that workstream added**, one extra row
(`gaming`). `1137`'s constants are identical old-vs-new and `row_ok` agrees on
**115,217 real rows, 0 disagreements**. The product repo's importer, run
against both shadow trees, produces a **byte-identical** manifest and 169
byte-identical sample files.

### One behaviour changed deliberately: `1137 plan` no longer writes `MANIFEST.csv`

It printed *"nothing written"* and then overwrote the manifest anyway, with
dry-run values — no `files`, no `largest_mb`, no codebook, no join columns,
because none of that work runs under `dry`. The manifest is the only record of
what was DELIVERED and `verify` reads it to decide whether a spreadsheet on
disk is an orphan, so one `plan` turned thirteen delivered datasets into
thirteen apparent orphans while reporting it wrote nothing. **Found by doing
it** — this workstream clobbered the live manifest that way. **A dry run that
writes is not a dry run.**

### Gate

`py -3 code/cedar_publication.py verify` — seven checks — wired into
`846_session_audit.py` as claim 30. **846 is 29/30**; the one FAIL is the
pre-existing "twelve customer datasets are not stale", owned by the 1137
workstream. `845 verify` ok. `293` adds no new finding on any file this
workstream touched. `62` red metrics are the ones already owned in the table
above — verified again here that the only one naming a file of ours,
`class2c 846_session_audit.py: fails += 1`, is present in `HEAD` with 846
stashed.

---

## GATE STATE AT THE CLOSE OF WORKSTREAM LINKAGE — 2026-09-02

*`code/1139_linkage_coverage.py`, `code/1140_linkage_close.py`, ADR-037. Build
log: `docs/LINKAGE_CLOSE_LOG_2026-09-02.md`.*

**GREEN and new:** `62_no_regression_check.py` now carries
`linkage_metrics_below_floor` (MUST_BE_ZERO), answered from `1139`'s own
baseline — the 293/845 arrangement, so it needed no re-recording of 62's
baseline. Measured **0**. Twenty-eight `linkage_*` counters print beside it.

**GREEN:** `293_lint_bug_classes.py` reports **no finding in either new
script**. One did land during the pass — `class2a` on `1140`'s
`row.setdefault(c, "")` — and was fixed at source with an explicit `if c not
in row` rather than waived; the call was genuinely not a no-op (the keys are
new columns absent from the input header) but a detector that cannot see that
is better answered with clearer code than with a waiver.

**GREEN:** `1131_attribution_method_vocabulary.py verify` — **0 drifts**. This
pass introduced `propagated_from_agent_ruling` on two tables and declared both
through `1131 declare`, with the reason on the record. It is deliberately
OUTSIDE `62`'s RULED set, the same choice `ladder_1122` made, so a propagation
can never move `tier_A_ruled` — ENTITY_MATCH_RULES rule 8.

**GREEN:** `1136_control_byte_gate.py verify` — 991 files, 0 control bytes.

### The two `846_session_audit.py` failures are NAMED, MEASURED, and NOT THIS WORKSTREAM'S

Standing rule: a red gate is not automatically yours, and saying so in writing
is the price of walking past it.

1. **`no NEW unsafe regenerating writer since the baseline`** —
   `845_regenerate_guard.py verify` names exactly one new writer:
   **`code/1143_methodology_papers.py`, markdown -> `docs/methodology/README.md`**.
   Script number 1143 was claimed after 1140; it is not a file this workstream
   wrote or touched. 3 of the 4 unsafe writers are pre-existing.
2. **`13 datasets are built and current`** — `1137_customer_dataset_combine.py
   verify` fails on *"contractors: NEVER BUILT - no spreadsheet exists"*.
   `dist/customer/contractors.xlsx` was **already absent at the start of this
   session** (as was `funding.xlsx`), because `1137.WORKBOOK_MAX_ROWS` is
   200,000 and `prime_contracts` is 1,217,768 rows — the workbook is
   deliberately not written and the verify asks for it anyway.
   `1137` is the **gaming workstream's** file and this pass was instructed not
   to edit it; it was not run either, because a build launched into another
   agent's live edit is how a half-finished storefront ships.

**Consequence that IS this workstream's to flag:** the ten new columns on
`data/clean/native_bills.csv` are not yet in `dist/customer/legislation.csv`.
A `1137 build` carries them through. Until then the storefront legislation
file still has no way to reach a Native entity.

## AGENTS THAT STALL, AND HOW TO TELL (2026-09-02)

One agent slept **5.4 hours** waiting on a build that never finished, wrote
nothing, and was killed with no result. Two rules came out of it, and the
second is the one that nearly cost a healthy agent its work.

### Rules every agent brief must carry

- **Never sleep more than 120 seconds in one call.** Poll in short intervals
  and print a progress line each time.
- **Never spend more than 15 minutes on any single external thing** - a fetch,
  a build, a subprocess. Abandon it, write down exactly where it stuck, move
  on. A partial result with an honest account beats silence.
- **Print progress every few minutes.** Silence is indistinguishable from
  death from outside.
- **Check whether the artifact already exists before waiting on it.** This
  project has repeatedly "discovered" sources already on disk: a 5,087-row SBA
  8(a) extract the spine builder already loaded, an 807-letter corpus recorded
  as unacquired, a 1.34 GB FAC bulk export.

### The liveness signal that LIES

A subagent's `.output` file mtime is **not** a liveness signal. Measured on
2026-09-02 with seven agents running: four showed 0.0 MB files and 20-41
minutes of silence and **all four were working** - one had just written
`code/1143_methodology_papers.py`, another `code/1148_nagpra_nps_databases.py`.
Killing on that signal would have destroyed live work.

**Use repo activity instead.** Files appearing under `code/`, `docs/` and
`review/` are ground truth that an agent is alive:

```python
now = time.time()
for p in list(Path("code").glob("*.py")) + list(Path("docs").glob("*.md")):
    if (now - p.stat().st_mtime) / 60 < 45:
        print(p)
```

The one unambiguous corpse had **322 minutes** of silence AND a zero-byte
output AND no file anywhere in the tree bearing its claimed script number.
Require all three before killing, and prefer sending the agent a message
first - a message forces a tool round, and a live agent answers it.

---

## 2026-09-02 · `62` IS RED AND NONE OF IT IS MONEY-RECON-1144 — the rule-15 naming

*Workstream MONEY-RECON-1144 ran `62_no_regression_check.py` at 17:33–17:41Z.
It exited with **22 regression lines**. Standing rule 15 forbids recording a
FAIL as "pre-existing, not mine" and walking away, and requires naming the line
and its owner here instead. This is that naming. Nothing below is a claim that
these are acceptable — it is a claim about **who can fix each one**.*

**First, the one that WAS mine, and is fixed.** `293` flagged
`class2c 1144_money_reconciliation_prime_sub.py: missing += 1` — a refusal
counter that named no key. `linkage_verify` now collects and prints the
offending `(source_dataset, subaward_source_record_id)` pairs instead of
tallying them. Re-run of `293` no longer names `1144` in any class.

**Second, the honest baseline.** `62` was **not green before this pass**, and
the shape of the diff says so on its own: `ship_tables_shipping` rose 197 → 227
and `harvest_source_rows_read` rose 2.1M → 13.2M in the same window. That is a
large shipping and acquisition wave landing from several agents, not the
footprint of one measurement pass that wrote 900 cells. `846` was already
**2 fail / 2 critical at `HEAD` (`bff0ba8`)** before MONEY-RECON-1144 began;
it is 2 fail / 1 critical now.

| regression | named owner | evidence |
|---|---|---|
| `regenerate_new_unsafe_writers = 1` | **workstream LINKAGE (`1139`/`1140`)** | `845 verify` names it exactly: `1139_linkage_coverage.py markdown -> docs/LINKAGE_COVERAGE.md`. Committed in `75d178b`, before this pass |
| `lint_class1` 0 → 1 | `1011_cross_dataset_reconciliation.py` | named by `293` |
| `lint_class2c` 60 → 69 | `1060` (×2), `1085`, `1086`, `846`, `852`, `873` | named by `293`. `1144`'s instance was the tenth and is fixed |
| `lint_class3` 0 → 2 | `1060_splink_pilot.py`, `992_newsletter_deal_candidates.py` | named by `293` |
| `lint_class4` 9 → 15 | `1030`, `1031`, `1111`, `1147`, `980`, `992` | named by `293`. **`1147` appeared mid-pass** — it did not exist when this workstream started |
| `lint_class6` (2 new sites despite the net fall) | `1077`, `30`, `518`, `870`, `99` | named by `293` |
| `lint_class7` 42 → 44 | `1030`, `1031` | named by `293` |
| `contract_violations = 16`, `contract_orphan_shippable = 11`, `tables_missing_from_25_TABLES` 179 → 243, `tables_missing_from_27_SPEC` 194 → 250, `tables_undocumented_in_codebook` 3 → 34, `tables_missing_codebook_block` 3 → 34, `tables_missing_notes_contract` 14 → 54, `ship_tables_at_zero` 13 → 53 | **workstream MONEY-FED-2026-09-02** (`1145_cosponsor_harvest.py`, `1147_released_host_directories.py`, `1148_nagpra_nps_databases.py`, `GRAIN_MONEY_FED` in `512`) | these are one event, not eight: a wave of new tables landed without codebook blocks. `512`'s working copy carries `GRAIN_MONEY_FED`, +131 lines, uncommitted at 17:35, and its own comment names the three scripts |
| `SHIPPING LOST: advocacy_passthrough_2026-08-07.csv`; `hearing_bill_links.csv` 465 → 464; `native_bills_subject_sweep.csv` 2,414 → 2,409 | **same wave** — a shipping-set regression, and `62` itself points at `tables_undocumented_in_codebook` as the usual cause | |
| `tier_A_ruled` FELL 1,676 → 1,669 | **NOT DETERMINED** | the metric reads `cedar_identifier_ledger_final.csv`, which MONEY-RECON-1144 never opened. Whoever wrote the ledger today owns it; this pass could not identify which of the nine concurrent agents that was, and says so rather than guessing |
| `rulings_unapplied` ROSE 1,215 → 2,894 | **NOT DETERMINED** | same. A near-tripling in one day is a large event and deserves a named owner it does not yet have |

**What MONEY-RECON-1144 touched, in full, so this table can be checked rather
than believed:** `code/1144_*` (new), the four stale figures in `512`'s
`GRAIN_SUBAWARD_FUNDING` descriptor string, marked blocks in
`MONEY_TOTALLING_RULES.md` / `KNOWN_ISSUES.md` / `ARCHITECTURE_DECISIONS.md` /
`WORK_QUEUE.md`, two `review/1144_*` files, and 900 cells on 290 rows of
`data/clean/subawards.csv` (rows and columns unchanged, money unchanged to the
cent, prior values retained). **It shipped nothing, registered no table, and
minted no tier.** None of the eight shipping-set metrics can be reached from
that surface.

**The two lines above marked NOT DETERMINED are the real debt in this
section.** Naming a file is not naming an owner, and `62`'s rule exists because
"not mine" is how six sessions in a row hid everything else this gate could
have said.

