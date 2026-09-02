# Deals — the identifier-driven sweep, 2026-09-02

*Build log for `code/1071_identifier_driven_deal_sweep.py`. Every figure below
was measured by that script on 2026-09-02 and is reproducible with
`py -3 code/1071_identifier_driven_deal_sweep.py measure`; the invariants it
enforces are in `docs/schema/1071_identifier_sweep_invariants.json` and
`… selftest` proves each one fires on a synthetic violation.*

**Nothing here was merged into `deals_classified.csv` (still 935 rows).** Three
review files were written; the merge is the deals owner's call.

---

## Why this wave exists

> *"We might need to update finding deals now that we have so many entities we
> can look through, and they have codes as well."*

Earlier deal discovery was driven by nation names. A subsidiary's legal name
routinely shares no token with its owner — ASRC Federal's operating companies
file as BROADLEAF, INUTEQ and VISTRONIX — so a name sweep cannot see them. Every
query in this wave starts from an identifier (UEI, CAGE) or from the register /
constellation-edge layer.

`code/1010_ownership_change_from_contracting.py` had already swept **one**
surface and **one** relation: `prime_contracts.parent_uei`. That was not
re-derived. Its `Hubs` resolver is imported so both scripts refuse intra-family
moves by identical logic, its 98 candidates are folded into the consolidated
set, and this wave adds the relations it never looked at.

| axis | relation | surface |
|---|---|---|
| S1 | `sub_parent_uei` changes under a fixed `sub_uei` | `subawards.csv` |
| S2 | `prime_parent_uei` changes under a fixed `prime_uei` | `subawards.csv` |
| C1 | one CAGE re-paired from one UEI to another | `prime_contracts.csv` |
| N1 | a fixed `awardee_uei` whose **legal name** changes family | `prime_contracts.csv` |
| A1 | a fixed `recipient_uei` whose **legal name** changes family | `federal_funding_transactions.csv` |

**N1 and A1 are the relations a name search cannot reach by construction: the
name is the thing that moved, and the UEI is what holds the before and the after
together.**

---

## The headline: 6 candidates, 1,821 refusals

| | count |
|---|---:|
| candidates from the five new axes | **6** (S1 4 · S2 1 · N1 1 · C1 0 · A1 0) |
| already carried by `deals_classified.csv` | 3 of 6 |
| **refusals written out beside them** | **1,821** |
| — intra-family relabelling | **544** |
| — same entity, re-registered or renamed in form only | 501 |
| — source artefact, not an event | 391 |
| — pass-through named as a parent, not an owner | 287 |
| — one side unnamed, battery untestable | 98 |
| — no tier-A Native side | 283 |
| consolidated open candidates across every workstream | **260** |

**544 candidates were rejected as intra-family relabelling** — the owner's
*"All Native Group → Ho-Chunk Inc, but it's still the same Native entity"*
case. That number is the measure of whether the detector can be trusted, and it
is 90× the number of things it let through.

### The six

| axis | identifier | before → after | FY | direction | in ledger? |
|---|---|---|---|---|---|
| S1 | `F2BEQJNKFY83` Clarus Fluid Intelligence | Clarus Fluid Intelligence → **Chestnut Park** | 2017→2019 | left Koniag | no |
| S1 | `DBD6KDKXWN65` Environmental Quality Management | EQM Technologies & Energy → **Arctic Slope Regional** | 2017→2021 | entered ASRC | **yes** — ANCSA2-2021-005 |
| S1 | `G81MSXW3MJR3` United Tribes Technical College | ND Assoc of Tribal Colleges → **UTTC** | 2021→2023 | entered | yes |
| S2 | `ZYDAV2TN2UU1` Brooks Range Contract Services | Soos Holding Company → **K'oyitl'ots'ina Ltd** | 2021→2023 | entered | yes |
| S1 | `PTJATEQ7Q873` WHPacific, Inc. | **NANA Regional Corporation → NV5 Global** | 2019→2021 | left NANA | **no** |
| N1 | `H3Y4JTE3SRJ4` | Blackfeet Utilities → "William Allen Talks About" | 2004→2005 | — | no (data defect) |

The two worth a reporter's time are **Clarus Fluid Intelligence leaving
Koniag** and **WHPacific leaving NANA for NV5 Global** — neither is in
`deals_classified.csv`, and both are visible only because the subawardee's UEI
stayed constant while its declared parent did not. Every row carries an
`interpretation_caution`; the most common one matters:

> *N fiscal years separate the two runs — the boundary is a GAP, not a date; the
> event lies somewhere in FYa–FYb.*

**A run boundary is not a transaction date.** No date from this sweep may be
written into a deal row as `Event_Date`.

---

## Four defects this sweep had to find before its own output was trustworthy

Each was caught because a candidate looked wrong next to one real row, which is
field-guide habit 3. Each is now a named refusal and is counted.

### 1. `cluster_v3` puts the Bureau of Indian Affairs inside Barrow

`cedar_identifier_ledger_final.csv` attributes **`Indian Affairs, Bureau Of`
(8 UEIs + 1 CAGE)** and **`Computer Sciences Corporation`** to
`AKNF-INPTBW-00-ARCSLO`, tier **B**, method **`cluster_v3`** — the same
name-cluster mechanism, and the same shape, as the Bristol Bay FA-01 defect
`START_HERE.md` records as closed on 2026-08-29. **It is not closed; it has
other victims.** There are 2,001 tier-B `cluster_v3` rows in the ledger.

Consequence, measured: **72 of `1010`'s 98 candidates do not survive a
tier-A-only re-test of their Native side.** `1010` resolves hubs from the whole
ledger at every tier. That is START_HERE trap 1 — *the exactness of the KEY says
nothing about the correctness of the LINK* — and it is why 1010's largest
candidate by dollars is General Dynamics IT attributed to Barrow.

**The fix here, not there:** this script separates **awarding** evidence from
**blocking** evidence. Awarding takes only the spine's own canonical / FR name
and ledger rows at `confidence_tier == 'A'`, and refuses outright any pair
carried at tier **X** (a negative ruling). Blocking uses everything, because
`ENTITY_MATCH_RULES` rule 7 permits weak evidence to refuse and never to award.
The folded 1010 rows are re-tested and carry
`tierA_native_side_confirmed` — **carried, not silently applied**: a consumer
must not assign a tier, and equally must not hide one.

### 2. `awardee_name` holds two renderings across the FY2007/FY2008 seam

Measured on the live file: FY2000–2007 prime rows come **only** from the
`Elijah hand-checked master prime file`, in Title Case (0–1 upper-case rows per
year); from FY2008 the `USAspending award_data_archive` adds ~41,500 rows a year
in UPPER CASE. This is the `extent_competed` two-vocabulary hazard
(`START_HERE.md` #5) on a different column, and it manufactured **19 of the
first run's 32 N1 candidates** — `Agviqs, Llc` → `AGVIQ LLC`, `Tc&S/F-W, L.L.C.`
→ `TC & S/F-W LLC`.

Both scanners now carry the run's dominant source vintage (`source_authority`
on prime, `source_vintage` on assistance, `source_dataset` on subawards) and a
transition whose two runs come from different vintages is refused as
`SOURCE_VINTAGE_SEAM` — **391 refusals**. *A change that coincides with a change
of SOURCE is not a change of OWNER.*

### 3. The spine puts an acronym inside the canonical name

`ANVC-TNDGSX-00` is recorded as **`Tanadgusix Corporation (TDX)`**, which
normalizes to `tanadgusix tdx` and therefore does **not** equal the
`TANADGUSIX CORPORATION` that FSRS prints. The consequence was not a missed
link, it was a **wrong report**: with the parent unresolvable, four TDX
subsidiaries whose reporting parent moved between two TDX registrations looked
like acquisitions out of nowhere — exactly the case the owner warned about.

Both name variants are now indexed (**561 parenthetical variants** across the
spine and ledger), and the four TDX rows are refused as
`INTRA_FAMILY_SAME_HUB`. `docs/NATIVE_ENTITY_NUANCES.md` records the same
parenthetical hazard on FR band names; this is the first time it has been
measured as a *false positive* generator rather than a false negative one.

### 4. A state is not an owner, and a blank is not an exit

FSRS `sub_parent_name` is free text typed by the reporting prime and is
routinely used to name the **pass-through**. The first run proposed *"Narragansett
Indian Tribe → STATE OF RHODE ISLAND"*, *"Crow Creek Sioux Tribe → STATE OF
SOUTH DAKOTA"* and *"Northwest Indian Fisheries Commission → STATE OF
WASHINGTON"* as ownership changes. **287 refusals**
(`GOVERNMENT_BODY_AS_DECLARED_PARENT`).

Separately, **98 transitions had one side with no name at all**. Every refusal
in the battery needs a name to test, so those rows sailed through as
`LEFT_NATIVE_FAMILY` purely because the other side could not be resolved. *An
empty cell is not a resolved absence.* They are now
`SIDE_NAME_MISSING` and are reported as untestable rather than as leads.

---

## What the constellation edge layer could and could not do

The mandate was to make the intra-family test rest on
`cedar_constellation_edges.csv`. It does, and here is the honest reach:

| | count |
|---|---:|
| edges in the file | 3,153 |
| edges with a `from_cedar_uid` — usable in the uid graph | **745 (23.6%)** |
| edges whose from-side is **name-only**, never minted | **2,408 (76.4%)** |
| distinct hubs on the to-side | 253 |

**Three quarters of the edge file cannot participate in a uid closure**, because
the from-side is a TERO certification, a 638 registration or a subsidiary
listing that has no spine row. Those 2,408 still carry `from_name` +
`to_hub_cedar_uid`, which *is* the subsidiary→owner fact this sweep needs, so
they are indexed **by name and used only to refuse** — a name may block, never
award. That is what lets a `BROADLEAF` be recognised as ASRC Federal's without
either name sharing a token with the other.

Minting the from-side of those 2,408 edges is the single change that would most
increase this sweep's reach.

---

## The consolidated candidate set

`review/1071_consolidated_deal_candidates.csv`, **260 rows**, de-duplicated on a
sorted-token key of party + counterparty + year + identifier. **126 duplicate
stagings were suppressed.**

| route | workstream | rows |
|---|---|---:|
| 1 — ownership change visible in contracting | `1010/prime_parent_uei` | 98 |
| | `1071/S1` · `S2` · `N1` | 6 |
| 2 — announced transaction | `993/tribal_wp_posts` | 111 |
| | `992/tribal_newsletters` | 30 |
| | `1032/sec_edgar` | 15 |

**70 of 260 already match a row in `deals_classified.csv`**; 190 do not. The
ledger match is deliberately conservative — ≥2 distinctive tokens plus an
overlapping year — so it under-claims rather than over-claims.

**`TERMS_STATED_RESTRICTIVE`:** no folded row came from a restricted host (host
census run over all 260). Eight contracting-derived rows name **NANA / Akima** as
a party and carry `terms_restricted_source`; they rest on federal contracting
data, not on NANA's own publications, and the flag is there so a publisher sees
the constraint before quoting anything NANA said.

**Nothing carries a value.** `announced_value_usd` is blank on every
contracting-derived row: no value was published and inferring one would be
fabrication. The dollar column that *is* populated,
`scale_obligations_usd_in_runs`, is the child's own obligations inside its own
declared runs — a scale figure, additive to nothing
(`docs/MONEY_TOTALLING_RULES.md`).

---

## Invariants, and the proof they fire

`py -3 code/1071_identifier_driven_deal_sweep.py selftest` injects one synthetic
violation per invariant, asserts the run exits 1 **and** that the named
invariant is what fired, restores, and asserts exit 0. All seven pass.

| | invariant |
|---|---|
| I1 | every candidate carries an identifier |
| I2 | no `nan` sentinel in any identifier column |
| I3 | every candidate's evidence note names the file **and** the fiscal years |
| I4 | no contracting-derived candidate carries an inferred value |
| I5 | refusals actually fired (an empty rejection file fails the run) |
| I6 | no duplicate dedup key in the consolidated set |
| I7 | no candidate's two sides fall in one family closure |

---

## Files written

```
review/1071_identifier_deal_candidates.csv        6 rows
review/1071_intra_family_rejections.csv       1,821 rows
review/1071_consolidated_deal_candidates.csv    260 rows
docs/schema/1071_identifier_sweep_invariants.json
docs/DEALS_IDENTIFIER_SWEEP_2026-09-02.md     (this file)
```

`duckdb` was used for the exploratory measurements behind axes C1/N1/A1
(1.2M-row prime scan in 12 s); the shipped script streams with `csv.reader` so
it carries no new dependency.

## What is closed, and what is not

**Closed:** C1 (CAGE re-pairing) yields nothing after the family battery — only
13 CAGEs in `prime_contracts.csv` are held by more than one UEI once the `nan`
sentinel is excluded, and all reduce to re-registration or intra-family. A1
likewise yields nothing: every assistance-side rename is either near-identical
or a vintage seam. **Do not re-run those two as a discovery route** without new
data.

**Open:** the 2,408 name-only constellation edges (mint the from-side); the
`cluster_v3` tier-B contamination of the identifier ledger, which is a defect in
a shared table and is therefore an owner decision, not an agent's repair.
