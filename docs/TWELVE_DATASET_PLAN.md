# The twelve-dataset plan — measured state and the route to READY

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

109 dated tables. Latest year present:

| latest year | tables |
|---:|---:|
| 2026 | **57** |
| 2025 | 21 |
| 2024 | 3 |
| 2023 | 9 |
| ≤2022 | 4 |

**78 of 109 tables are current through 2025 or 2026.** Of the 30 ending
earlier, most are **archives by design, not staleness** — `faads_*` is
explicitly the FY2000–2007 backfill, `sam_prime_contracts_fy2000_2007` says so
in its name, `tcu_roster` carries founding years back to 1962.

**The distinction matters and we do not currently record it.** A table ending
in 2007 because that is its era is healthy; a table ending in 2023 because
nobody re-pulled it is a gap. Action: add `coverage_intent`
(`current` | `archive` | `point_in_time`) to the dataset contract, so the
scoreboard can tell them apart and flag only the real ones.

### Identity — the honest number is 48%

**2,195,145 entity-bearing rows scanned; 1,053,435 carry a Cedar id (48.0%).**

42 tables sit under 75% keyed. The concentration is extreme — a handful of
very large tables account for most of the unkeyed mass:

| table | keyed |
|---|---|
| `faads_transactions_all_agencies.csv` | **0%** (2.77M rows) |
| `faads_transactions.csv` | 0% (60,661) |
| `grantmaker_funding_flows.csv` | 0% (18,656) |
| `ferc_ex_parte_parties.csv` | 0.2% (4,246) |
| `entity_candidates_new/rejected` | 0% — correct, these are *candidates* |

**This is the single biggest lever in the project.** Keying FAADS alone moves
the global figure by roughly 20 points, and it is one dataset, one join path.

### The master list — 1,536 distinct Native entities, permanently identified

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

Every one has a permanent `CE-XXXXX-CC` that never changes, plus a mutable
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

## The route: all twelve, in dependency order

Ordered so that each wave unblocks the next, not by size.

### Wave 1 — the identity lever (unblocks measurement everywhere)

**1. `funding` (FAADS).** 0% keyed across 2.77M rows, the largest single
uncertainty mass in Cedar. It also carries the destroyed-identity defect
already diagnosed in `prime_contracts` (a transaction feed projected onto a
schema with no modification number) and needs a full re-extract. Doing this
one first turns the global keyed figure from 48% to roughly 68% and gives
every downstream measurement a real denominator.

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
