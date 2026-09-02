# Dataset 13 — the entity layer (the hub)

*Hand-maintained. Created 2026-09-01 by workstream DOCS.*

> **Why this file did not exist until today.** The readiness scoreboard has
> always counted thirteen datasets and `code/24_generate_dataset_docs.py`
> generates eleven. `native-owned-businesses` and `natural-resources` have
> hand-written docs. `_entity_layer` had **none** — so the one collection every
> other dataset joins through was the only one with no maintenance doc, and the
> owner's standing complaint that *"it seems like you're missing stuff for
> every dataset"* was literally true for the hub. This closes that.

---

## What this is

The entity spine, the identifier ledgers, the ruling ledgers and the reference
rosters. It is **infrastructure — it is not sold**, and `518` grades it on the
same ten contract points as a shelf product because everything on the shelf
joins through it. A defect here is a defect in all twelve other datasets at
once.

`docs/datasets/README.md` indexes the sellable datasets; this one is the thing
they have in common.

## Where the numbers live

| | file | what it is |
|---|---|---|
| the register | `data/spine/cedar_identity_register.csv` | the minted `cedar_uid` and its handle. **The one data file git tracks**, precisely so a silent change to it cannot be undetectable. |
| the spine | `data/spine/cedar_entity_spine.csv` | one row per Native entity, with class, state, hierarchy and evidence columns |
| the assertion store | `data/clean/cedar_assertions.csv` | append-only; a fact is never edited, it is asserted again |
| the resolved view | `data/clean/cedar_resolved_facts.csv` | what Cedar stands behind, computed from ordered public rules |

Live counts, re-measured 2026-09-01: **1,555 register rows · 1,555 spine rows ·
34,615 assertions · 34,275 resolved facts · 338 refutations · 0 conflicts.** Do
not copy those into another document — read them from
`docs/DOC_STALENESS.md`, which is regenerated from the files, or re-measure.

## Coverage here is not a year range

Every other dataset's coverage question is *"which years do we hold?"* This
one's is **"which entities do we know about, and how fast is that list going
stale?"** — and the two fail differently. `docs/REFRESH_CADENCE.md` puts it
plainly: a refresh that runs too slowly gives you stale numbers, which every
reader can see; a **discovery** pass that runs too slowly gives you confidently
wrong numbers, which no reader can see, *because a missing entity leaves no
hole in the table.*

The measured drift, from `code/276_measure_discovery_gap.py` (do not re-derive
it here — quote it):

| FY | rows a UEI-only pull would lose |
|---|---:|
| FY2015 | 0.23% |
| FY2019 | 6.24% |
| FY2023 | 7.49% |
| FY2024 | 8.74% |
| **FY2025** | **12.66% — +3.9 pp in one year** |

And on the flag route, **9,719 entities carry a Native business-type flag in
FPDS prime data that the identifier route has never seen — 76.9% of all flagged
entities, $70.96B of obligations.**

**Read those together: coverage of the known population is fine and the known
population itself is drifting**, and the drift accelerated from about 1 pp/yr
(FY2019–23) to 3.9 pp in FY2025. Quarterly discovery is the right cadence and
it is a different job from a refresh.

## The ownership spiderweb, and the trap in counting it

`data/clean/fpds_uei_edges.csv` holds **5,167 rows**, and that is *not* the
ownership figure. Re-measured 2026-09-01:

| `edge_type` | rows | is it ownership? |
|---|---:|---|
| `parent_uei` | 2,726 | yes |
| `ultimate_parent_uei` | 1,891 | yes |
| `prime_to_sub` | 550 | **no — a contracting relationship** |

**4,617 ownership edges over 2,725 registrants.** A further 99 rows carry
`blocklisted_parent = 1` and must be excluded from any attribution. Filter
`edge_type` before you count; quoting 5,167 books 550 subcontracts as corporate
parentage. Full derivation and the Ho-Chunk / Winnebago worked case:
`docs/NATIVE_ENTITY_NUANCES.md`.

The caveat that makes the spine necessary, in the owner's words: the declared
highest-level owner in a federal database is often the highest *incorporated*
owner — Ho-Chunk, Inc., not the Winnebago Tribe of Nebraska — because the tribe
itself need not hold a CAGE in the chain. **That last hop, holding company →
tribe, is Cedar's proprietary edge** and no federal database supplies it.

## NEVER do these

- **Never re-mint a `cedar_uid`.** The identity contract promises the uid does
  not move. `62_no_regression_check.py` fails the build on a reassignment and
  its own note says *do NOT re-record the baseline until you know why*.
- **Never edit an assertion.** The store is append-only; a disagreement is a
  new assertion by a different source, which is the whole design.
- **Never run `01_build_entity_spine.py` or `09_import_rulings.py` casually** —
  `518` grades this collection's rebuild **DESTRUCTIVE** and that is one of its
  open contract points.
- **Never resolve a name to an entity outside `503.resolve()`.** The
  `ADMIN_GEOGRAPHY` / `CIVIC_FORM` guards removed 1,403 false resolutions and
  a hand-rolled match reintroduces every one of them. See
  `docs/RESOLUTION_RULES_LEARNED.md`.
- **Never treat an absent negative as a negative.** `entity.is_federally_recognized`
  asserts `yes` for entities on the roster and asserts **nothing** for those
  off it.

## Known issues and caveats

- **`identity_facts_legacy_only` is gated in the wrong direction** — it sits in
  `62`'s `MUST_NOT_FALL` under a comment reading *"This may only fall"*, while
  `docs/EXTERNAL_REVIEW_RESPONSE.md` records it as MUST_NOT_RISE. Filed as a
  one-line change request against `62`'s owner.
- **Corroboration fell 38 → 4 independent-family facts and nobody measured
  why.** See `docs/ASSERTION_LAYER.md`. Do not quote either number to a buyer
  until the `lineage_ancestry` diff is run.
- **1,279 of 1,555 spine rows still carry no `verification_route` and no
  `evidence_tier`** (82.3%). The numerator has not moved; the denominator grew
  when 19 IHS consortia were promoted, and all 19 arrived with evidence.
- **`entity.city` is on 229 of 1,555 rows (14.7%)**, so it is effectively
  single-sourced and there is almost nothing for a second source to corroborate.
- **The `503` zero-loss guarantee was measured against a 1,536-row spine** and
  has not been re-measured against the 19 names added since.

## Refresh

**Cadence:** discovery quarterly (see the drift table above); the identifier
ledgers follow whichever dataset feeds them.

**Rebuild:** `py -3 code/build.py run _entity_layer --execute` — and read the
DESTRUCTIVE warning above first.

## Reference

- `docs/ASSERTION_LAYER.md` — the append-only fact store and its resolution rules
- `docs/NATIVE_ENTITY_NUANCES.md` — what counts as a Native entity, and the ownership boundary
- `docs/IDENTIFIER_STANDARD.md` — UEI / CAGE / EIN / `tribe_id` conventions
- `docs/RESOLUTION_RULES_LEARNED.md` — R1–R2, the guards and their counter-examples
- `docs/ENTITY_MATCH_RULES.md` — why a denylist of phrasings loses to a predicate
- `docs/REFRESH_CADENCE.md` — refresh vs discovery, and the measured lag profile

---

<!-- CEDAR:COVERAGE-MEASURED collection=_entity_layer START -->

## Readiness and coverage — measured, never hand-typed

*The status line and the `Years Cedar holds` column below are regenerated by `py -3 code/621_dataset_coverage.py` (tables measured 2026-09-01) and `py -3 code/518_dataset_readiness.py`. Do not edit them by hand; edit the table and re-run. The `Years upstream` research around this block is authored and is NOT touched by the generator.*

**Status: BLOCKED** — 35 customer tables, shelf `infrastructure`, measured 2026-09-01 by `518`.

**Open contract points, with the tables that carry them:**

- C1 grain UNSTATED on 6: cedar_identifier_graph_edges.csv, cedar_ruling_ledger_consolidated.csv, cross_dataset_ruling_map.csv
- C2 no validated primary key on 6
- C3 literal duplicates: cedar_identifier_graph_edges.csv(2,451), cedar_ruling_ledger_consolidated.csv(6,302), cross_dataset_ruling_map.csv(2,228)
- C8 rebuild is DESTRUCTIVE (01_build_entity_spine.py, 09_import_rulings.py) - no safe documented rebuild path

Next action: **C1 grain UNSTATED on 6: cedar_identifier_graph_edges.csv, cedar_ruling_ledger_consolidated.csv, cross_dataset_ruling_map.csv**.

| contract point | state |
|---|---|
| C1 grain stated | 29/35 |
| C2 validated primary key | 29/35 |
| C3 literal duplicates | 10,985 rows |
| C4 identity path | HUB (dataset 13) |
| C5 row conservation | 1/35 |
| C6 unresolved conflicts | 0 shipped as definite |
| C7 double counting | none |
| C8 rebuild path | DESTRUCTIVE |
| C9 update documented | see docs/datasets/ |
| C10 gates | 62 + semantic diff |

### Years Cedar holds — per table, measured from the live file

| Table | Rows | Period column | Years Cedar holds |
|---|---:|---|---|
| `admin_region_assignments.csv` | 2,124 | — | no dated column |
| `admin_region_overlap_derived.csv` | 28 | — | no dated column |
| `admin_region_systems.csv` | 6 | — | no dated column |
| `admin_regional_observations.csv` | 27 | — | no dated column |
| `admin_regions.csv` | 155 | — | no dated column |
| `bie_uio_dollars_by_entity.csv` | 114 | — | no dated column |
| `bie_uio_identifier_links.csv` *(internal-by-decision)* | 302 | — | no dated column |
| `cedar_correction_register.csv` | 178 | — | no dated column |
| `cedar_entity_identity_crosswalk.csv` | 10,107 | — | no dated column |
| `cedar_entity_spine.csv` *(unregistered)* | — | — | **not built** |
| `cedar_identifier_graph_edges.csv` | 46,051 | — | no dated column |
| `cedar_identifier_graph_nodes.csv` | 115,471 | — | no dated column |
| `cedar_identifier_ledger.csv` *(unregistered)* | — | — | **not built** |
| `cedar_identifier_ledger_final.csv` | 20,577 | — | no dated column |
| `cedar_identifier_ledger_tiered.csv` *(internal-by-decision)* | 19,232 | — | no dated column |
| `cedar_identifier_propagation.csv` | 1,157 | — | no dated column |
| `cedar_publishable_identifiers.csv` | 1,577 | — | no dated column |
| `cedar_ruling_ledger_consolidated.csv` | 15,587 | `ruling_date` | 2026 |
| `cedar_rulings.csv` *(unregistered)* | — | — | **not built** |
| `cross_dataset_ruling_map.csv` | 7,507 | — | no dated column |
| `entity_aliases.csv` | 6,298 | — | no dated column |
| `entity_candidates_new.csv` *(internal-by-decision)* | 2,874 | — | no dated column |
| `entity_candidates_rejected.csv` *(internal-by-decision)* | 1,045 | — | no dated column |
| `entity_evidence_profile.csv` *(internal-by-decision)* | 1,313 | — | no dated column |
| `entity_hierarchy.csv` | 952 | — | no dated column |
| `entity_name_harvest.csv` *(internal-by-decision)* | 31,728 | — | no dated column |
| `entity_relationships.csv` | 2,292 | — | no dated column |
| `entity_year_coverage.csv` *(internal-by-decision)* | 196 | `year` | 1999–2026 |
| `entity_year_panel.csv` | 12,534 | `year` | 1999–2026 |
| `federal_recognition_events.csv` | 366 | `effective_date` | 1996–2026 (interior gap: 1999, 2001, 2004, 2006, 2011, 2017, +1 more) |
| `federal_recognition_roster.csv` | 17,058 | `publication_date` | 1995–2026 (interior gap: 1999, 2001, 2004, 2006, 2011, 2025) |
| `foia_discovery_targets.csv` | 122 | — | no dated column |
| `foia_request_index.csv` | 9,481 | — | no dated column |
| `intertribal_memberships.csv` | 989 | — | no dated column |
| `intertribal_orgs.csv` | 57 | — | no dated column |
| `native_fi_roster.csv` | 94 | — | no dated column |
| `nho_doi_notification_roster.csv` | 190 | — | no dated column |
| `nho_ito_spine_crosswalk.csv` *(internal-by-decision)* | 269 | — | no dated column |
| `nho_ownership_changes.csv` | 9 | `effective_date` | `effective_date` present, **0 rows parse to a year** |
| `nho_parents.csv` *(internal-by-decision)* | 21 | — | no dated column |
| `nho_register.csv` | 218 | — | no dated column |
| `nho_verified_entities.csv` | 36 | — | no dated column |
| `tcu_cdfi_added.csv` | 130 | — | no dated column |
| `tcu_cdfi_ownership_evidence.csv` | 130 | — | no dated column |
| `tcu_roster.csv` | 37 | — | no dated column |
| `visitor_access_events.csv` | 20 | — | no dated column |
| `visitor_record_foia_requests.csv` | 667 | — | no dated column |

<!-- CEDAR:COVERAGE-MEASURED collection=_entity_layer END -->
