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
| `native_entity_lobbying_disclosures.csv` | 350 | `code/lobbying_pull/05_match_filings_v2.py` — a FULL rebuild from `raw_filings.jsonl` that reverts **65 and 350 both**. If 05 is ever re-run: 65, then 350, then 351, then 353. |
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
| `lint_class2c` NEW ×2 | no | `852_extend_constellation_edges.py` (`dropped += 1`), `873_build_aiannh_crosswalk.py` (`nskip += 1`) |
| `lint_class3` NEW ×1 | no | `992_newsletter_deal_candidates.py` |
| `lint_class4` NEW ×3 | no | `1030_sec_edgar_native_transactions.py`, `1031_ancsa_45_55_139_annual_reports.py`, `992_newsletter_deal_candidates.py` |
| `lint_class7` NEW ×2 | no | `1030_…`, `1031_…` (`candidate_id: f"…{n:06d}"`) |
| `lint_class6` NEW ×3 | no | `518_dataset_readiness.py`, `870_build_geo_crosswalks.py`, `871_promote_geo_keys_contracts.py` |
| `files_with_columns_lost_vs_backup = 2` | no | `entity_evidence_profile.csv` (505, already named above in this file) and **`federal_funding_tribe_year_panel.csv` — NEW: `tribe_id` and `tribe_id_scheme` lost against `.bak_2026-09-01_pre843`.** Owner: whoever ran 843. **Neither of our two enriched tables lost a column**; both gained only. |
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
