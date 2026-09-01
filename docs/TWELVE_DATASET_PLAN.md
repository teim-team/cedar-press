# The twelve-dataset plan — measured state and the route to READY

> ## SUPERSEDED IN PLACES, 2026-09-01 evening. Read this box first.
>
> Four workstreams (inventory, ruling-mining, spiderweb harvest, universe gaps)
> landed after this page was written and moved several of its numbers. The
> reasoning below still stands; these figures replace the ones in the body:
>
> | this page said | actually |
> |---|---|
> | identity keyed **48%** | **44.3%** — the old denominator was smaller than one member table |
> | grain unstated on **207** tables | **25** |
> | `prime_contracts` **80,778 duplicates** | **0** — they were distinct FPDS transactions; a de-dupe would have DELETED real rows |
> | declared ownership edges **2,901** | **5,167** — the ingest was reading 6 of 40 files carrying a parent UEI |
> | master list **1,536** entities | **1,555** — 19 IHS self-governance consortia promoted |
> | FAADS lever "**~20 points**" | **+39 points** |
>
> **New since:** `$1,783,253,649` found unattributed on one UEI (Tanana Chiefs
> Conference filing as DENA NENA HENASH) and fixed; the resolver was
> contradicting recorded human refusals **47%** of the time, now 57% less;
> `docs/datasets/_PUNCHLIST.md` turns the standard into **418 named actions**.
>
> **The live plan is the punch list.** This page is the reasoning behind it.


*Written 2026-09-01. Every number here was measured from live data today, not
recalled. Companion to `docs/DATASET_READINESS.md` (the scoreboard) and
`NEXT_SESSION.md` (the immediate queue).*

This answers four questions the owner asked in one sitting, because they turn
out to be the same question asked from four sides:

1. Do we have a sustainable way to fact-check and maintain these datasets?
2. Does every Native thing we've identified have an ID, and does every entry carry it?
3. When a deal or contract involves several Native parties, do we capture all of them?
4. Do we have the full universe of years available?

---

## Where we actually are

**READY 2 / 13** — `nagpra`, `federal-register`.

### Year coverage — better than expected, and the gaps are mostly deliberate

**RE-MEASURED 2026-09-01 (workstream H) and now regenerable** —
`py -3 code/521_inventory.py`, per-table figures in `docs/INVENTORY.md`. This
section read *"109 dated tables · 57 at 2026 · 78 of 109 current"*; the scan
behind it saw fewer than half the dated tables it could have. Scope is stated
explicitly this time: **the 210 SHIPPABLE tables**, coverage columns only, with
provenance stamps (`fetched_date`, `classified_date`, …) refused by name so
Cedar's own clock is never read as the data's coverage.

| latest coverage year | shippable tables |
|---:|---:|
| 2026 | **123** |
| 2025 | 22 |
| 2024 | 2 |
| 2023 | 2 |
| ≤2022 | 16 |
| no coverage column at all | 45 |

**145 of 165 dated shippable tables are current through 2025 or 2026** — 88%,
against the 72% this section used to report. Of the 20 ending earlier, most are
**archives by design, not staleness** — `faads_*` is explicitly the
FY2000–2007 backfill, `sam_prime_contracts_fy2000_2007` says so in its name,
`tcu_roster` carries founding years back to 1962.

A further **13 tables carry dates beyond 2026** — compact expiries, bond
maturities, FPDS `2099` period-of-performance sentinels. Those are not
coverage and are counted at 2026 above rather than being allowed to overstate
how current the data is; they are named in `docs/INVENTORY.md`.

**The distinction matters and we do not currently record it.** A table ending
in 2007 because that is its era is healthy; a table ending in 2023 because
nobody re-pulled it is a gap. Action: add `coverage_intent`
(`current` | `archive` | `point_in_time`) to the dataset contract, so the
scoreboard can tell them apart and flag only the real ones.

### Identity — the honest number is 44%

**CORRECTED 2026-09-01 (workstream H).** This section read *"2,195,145
entity-bearing rows scanned; 1,053,435 carry a Cedar id (48.0%)"*, and that
figure contradicted the table printed immediately below it: the denominator
2,195,145 is **smaller than `faads_transactions_all_agencies.csv` alone**
(2,769,748 rows), which the same table lists as entity-bearing and 0% keyed. A
scan that reports a total smaller than one of its own members has skipped
something.

Re-measured with the definition stated explicitly, and now regenerable:

> A table is **entity-bearing** if its header carries `cedar_uid` or one of the
> eighteen id columns in `503_identity.ID_COLS` (imported by
> `code/521_inventory.py`, not copied). A row is **keyed** if that column holds
> a non-empty, non-null-word value.

**134 entity-bearing tables · 7,250,710 rows · 3,215,604 carry a Cedar id
(44.3%).** Regenerate with `py -3 code/521_inventory.py`; the per-table figures
are in `docs/INVENTORY.md`.

**46 tables sit under 75% keyed** (the section previously said 42). The
concentration is extreme and the direction of the lever is unchanged — a
handful of very large tables account for most of the unkeyed mass:

| table | keyed |
|---|---|
| `faads_transactions_all_agencies.csv` | **0%** (2.77M rows) |
| `faads_transactions.csv` | 0% (60,661) |
| `grantmaker_funding_flows.csv` | 0% (18,656) |
| `ferc_ex_parte_parties.csv` | 0.2% (4,246) |
| `entity_candidates_new/rejected` | 0% — correct, these are *candidates* |

**This is the single biggest lever in the project**, and on the corrected
denominator it is a bigger lever than this section used to claim. Keying the
two FAADS tables alone (2,830,409 rows at 0%) moves the global figure from
**44.3% to 83.4%** — 39 points, not the ~20 stated before 2026-09-01 — and it
is one dataset, one join path.

### The master list — 1,555 distinct Native entities, permanently identified

| class | n | | class | n |
|---|---:|---|---|---:|
| Federally recognized tribe | 349 | | Intertribal Organization | 56 |
| Fed. recognized AK Native Village | 228 | | Individually Native-owned business | 45 |
| Native Hawaiian Organization | 210 | | Urban Indian Organization | 43 |
| BIE School | 185 | | Tribal College or University | 37 |
| ANCSA Village Corporation | 173 | | Native Financial Institution | 29 |
| Native CDFI | 64 | | Federal constituency entity | 22 |
| State-recognized tribe | 64 | | ANCSA Regional Corporation | 12 |
| | | | Self-governance consortium | 10 |
| | | | ANCSA Group Corporation | 6 |
| | | | State constituency entity | 3 |

**On the 210 NHOs — the owner's question, answered:** 179 of them come from
the DOI ONHR notification list (`doi_roster_only`); the rest are NHOA members,
self-statements and one ruling. Only **15 carry any federal identifier** and
only **6 have prime contract dollars**. So 210 is right for the DOI universe
and 6 is right for NHOs visible in contracting — different questions, both
true. At 7% identifier coverage it is the largest proportional identity gap in
the master list.

Every entity has a permanent `CE-XXXXX-CC` that never changes, plus a mutable
display handle with full history. This is the compiled master list; it is
`data/spine/cedar_identity_register.csv` and it is the one table git tracks.

### Multi-party — the capability exists, but is not applied consistently

Measured on the three tables where it matters most:

| table | plural id column? | rows holding >1 entity |
|---|---|---:|
| `nagpra_notices` | **yes** — `consulted_entity_ids`, `affiliated_entity_ids`, `disposition_priority_entity_ids` | works as designed |
| `admin_appeal_decisions` | yes (`native_entity_ids`) | **0** — plural column, never more than one value |
| `deals_classified` | **NO** — `native_party_entity_id`, singular | cannot represent it at all |
| `compacts` | no — `tribe_id` | 0 |

**Sized:** 12 of 935 deals name more than one spine entity *in their own
text* while the schema records one. One names **six** and records none —
`NTIA TBCP award: Santa Fe Indian School`.

Small today, structural forever. A federal award to a consortium, a joint
venture, a multi-tribe compact and a passthrough grant are all natively
many-to-many, and every one of those is in scope.

**Action:** promote deals and appeals to the nagpra pattern — a party *bridge*
table at (deal, entity, role) grain rather than a column on the deal. The
bridge is the correct shape and we already run one for nagpra with 51,521 rows.

---

## The sustainable maintenance answer

The machinery for this now exists; what was missing was that it ran on the
architecture rather than on the datasets. Six things make a dataset
maintainable, and each has exactly one place it lives:

| question | answered by | command |
|---|---|---|
| Can we ship it? | the scoreboard | `py -3 code/518_dataset_readiness.py` |
| What is one row? | the contract | `py -3 code/512_build_dataset_contracts.py verify` |
| May a buyer total it? | export safety | `py -3 code/517_export_safety.py` |
| Did we lose source rows? | conservation | in `cedar_harvest_conservation.csv`, gated by I13 |
| Did anything change silently? | semantic diff | in `62`, snapshots by CONTENT |
| How do I update it? | the runbook | `docs/datasets/<name>.md` |

**The acceptance test for maintainability is not that a runbook exists.** It is
that *a different session can execute it from the document alone, with no
history knowledge.* That is contract point C9 and **it has not yet been tested
for either READY dataset.** Testing it is the next verification task, and it
may demote a dataset. That is the point.

---

## Do this FIRST: `docs/SPIDERWEB_LEARNING_PLAN.md`

Measured 2026-09-01 (revised the same day, the ingest was reading 6 of 40 source files): of 5,167 declared ownership edges, **1,097 have exactly
one end keyed** — each a named firm a registrant declared into the corporate
family of an entity we already know, and we are discarding the identification
it hands us. The identifier graph (115,471 nodes / 46,051 edges) is built and
essentially unmined.

Harvesting that before the next build round raises identity coverage across
every dataset at once, and several datasets are blocked on exactly the
knowledge it would produce. It also carries the multi-party and
ownership-continuity work, which are schema changes better made before more
tables are declared READY against the current shape.

## The route: all twelve, in dependency order

Ordered so that each wave unblocks the next, not by size.

### Wave 1 — the identity lever (unblocks measurement everywhere)

**1. `funding` (FAADS).** 0% keyed across 2.77M rows, the largest single
uncertainty mass in Cedar. It also carries the destroyed-identity defect
already diagnosed in `prime_contracts` (a transaction feed projected onto a
schema with no modification number) and needs a full re-extract. Doing this
one first turns the global keyed figure from **44.3% to roughly 83%**
(corrected 2026-09-01; this read "48% to roughly 68%" against a denominator
that had silently omitted the 2.77M-row table it was about) and gives every
downstream measurement a real denominator.

### Wave 2 — the closest to the line (one blocker each)

**2. `native-owned-businesses`** — one blocker, C5 row conservation. Copy the
pattern from `nagpra` or `federal-register`; both work.
**3. `contractors`** — grain now 8/10 after the entity-year regrain; finish
`fpds_uei_cage_map` and `contractor_ranking`, both of which have open rulings
with evidence already attached.
**4. `subcontracting`** — one grain blocker (`subawards`), plus 10,770
suspected-legitimate duplicates of the same shape `prime_contracts` turned out
to have. Prove or disprove that shape before touching the data.

### Wave 3 — the multi-party promotions

**5. `deals`** — build the party bridge. 12 known multi-party deals today, and
this is the dataset where joint ventures live, so the number only grows.
**6. `lobbying`** — 34 tables, 5 grain blockers; also the registrant/client
relationship is natively many-to-many.
**7. `legislation`** — 2 grain blockers, both small; bills have many sponsors
and many affected entities.

### Wave 4 — the domain-heavy remainder

**8. `gaming`** (46 tables, the largest), **9. `nonprofits`**,
**10. `natural-resources`**, **11. `_entity_layer`** (35 tables — internal but
it gates everything else's identity claims).

### Already READY, and to be kept there

**12. `nagpra`** · **13. `federal-register`** — both need their C9 runbook test
executed by an independent session before we treat them as proven.

---

## The three standing measurements

Re-run these every pass; they are the product, not the machinery.

```
py -3 code/518_dataset_readiness.py     # READY x / 13
py -3 code/517_export_safety.py         # tables a buyer may aggregate
py -3 code/62_no_regression_check.py    # nothing silently regressed
```

Target for the next pass: **READY 4 / 13**, global keyed above 65%, and the
deals party bridge standing up with its first multi-party rows.
