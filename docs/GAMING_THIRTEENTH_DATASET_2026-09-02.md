# Gaming becomes the thirteenth built dataset, and the collection gets a quality pass

*Written 2026-09-02, workstream `GAMING-THIRTEENTH-1141`. Every number below was
measured against the live files that day and the command that measures it is
named beside it. Model decision: **ADR-036**.*

Owner, 2026-09-02: *"you're always working on thirteen datasets, the twelve in
Cedar Press, and then the gaming dataset. Those are the ones that you're always
prioritizing."* And, separately: *"don't focus on building more, focus on
making everything we have good."*

---

## 1. The build set and the storefront set were one tuple

`1137_customer_dataset_combine.py` decided who gets a combined spreadsheet with
`CUSTOMER_SHELVES = ("standard", "pro")`. That tuple answered two questions:
**where is this sold** and **is this delivered**. `gaming` is `shelf: grove` —
it goes out through Cedar Grove and belongs on no Cedar Press shelf — so the
one test excluded it from the product build as well.

**Gaming is the largest maintained collection in the project: 65 tables, 56 of
them `shippable`.** It had no combined spreadsheet, no codebook and no notes,
and `846_session_audit`'s CRITICAL deliverables claim was green throughout,
because that claim counted the storefront too.

### What changed

`code/cedar_publication.py` now declares three sets and every consumer says
which it means:

| set | shelves | n | meaning |
|---|---|---:|---|
| `STOREFRONT_SHELVES` | `standard`, `pro` | 12 | sold on Cedar Press |
| `GROVE_SHELVES` | `grove` | 1 | sold through Cedar Grove |
| `BUILD_SHELVES` | all three | **13** | delivered |

`CUSTOMER_SHELVES` survives as an alias for the storefront, which is what it
always meant. `MANIFEST.csv` gains `storefront` (Y/N) and `sold_through`, so a
reader of the OUTPUT cannot re-conflate them either.

`1137 build <dataset> [...]` now restricts a pass to named datasets and MERGES
the manifest rather than replacing it. A full pass rewrites a 1.6 GB
deliverable; rebuilding one dataset must not require rebuilding all of them,
and a partial pass that dropped the other twelve manifest lines would
manufacture twelve orphans.

### The "silent extra dataset" property survives, three ways

The count was hard-coded because `newsletters` shipped as an unwanted
thirteenth storefront slot before the owner withdrew it, and nothing failed.
`1137 verify` now holds that:

1. a thirteenth **storefront** slot fails the storefront count;
2. a fourteenth **built** dataset fails the build count;
3. a spreadsheet on disk that **no manifest line claims** fails outright.

The third is new. Proved by fixture — dropping an empty `newsletters.csv` into
`dist/customer/` turns `verify` red and names it; removing it turns it green.

### What gaming delivers

```
gaming    787 rows x 311 cols   +187 joined   1 file
```

`gaming.csv`, `gaming__CODEBOOK.md`, `gaming__NOTES.txt`, `gaming__NOTES.pdf`.

**Zero `casino_city_id` and zero D-U-N-S columns in the delivered file** —
Casino City Press identifiers are licensed internal-only and `DROP_COLS` takes
them out as columns, not rows. Verified on the shipped header.
`gaming_facility_metrics.csv` and `gaming_property_capacity_history.csv` are
`licensed-never-ships` in the contract and are never folded in.

**The settled denominator is unchanged: 717 distinct `cedar_place_id`**, from
787 rows less 16 `NOT_A_PLACE` less the 54 extras collapsed by 53 adjudicated
MERGE groups. Read, never recomputed.

---

## 2. Two defects in `1137` that gaming exposed, fixed for all thirteen

### 2a. The shared join key was the first one DECLARED, not the finest

`gaming_facilities.csv` declares `key_columns = [tribe_id, cedar_uid,
entity_id, facility_id]` and its grain is the PROPERTY: 787 rows, 787 distinct
`facility_id`, 250 distinct `tribe_id`. The join loop took the first declared
key both tables carried, so it joined on `tribe_id`.

Every one-to-many count column therefore counted the property's whole NATION.
`n_gaming_revenue_bounds` on a Cherokee Nation property reported the tribe's
total, on all ten of its casinos. **The column is named for the property and
counted for the tribe** — this project's signature defect in one cell.

Keys are now ranked by how finely they cut the flagship (most distinct
non-blank values wins, declared order breaks ties). Effect on gaming: four more
tables meet the one-to-one test at facility grain and fold in properly
(`gaming_nigc_roster_link`, `gaming_properties`,
`gaming_property_federal_traces`, `loyalty_program_property`), and 22 count
columns moved from tribe grain to property grain.

`loyalty_programs` is the one table that still folds in on `tribe_id`, and it
was checked: `join_cardinality tribe_id: one`, `measured_rows_per_join_key: 1`,
and live it is 18 rows with 18 distinct `tribe_id`. It is a genuine tribe-grain
attribute spread across that tribe's properties — a denormalisation, not a
cardinality error.

### 2b. `plan` overwrote the manifest while printing "nothing written"

Found by running it. The manifest is what `verify` reads to decide whether a
spreadsheet is an orphan, so a dry run could turn twelve delivered datasets
into twelve apparent orphans. Fixed the same hour, independently, by the owner.

### 2c. Column ORDER, not column deletion

`gaming` lands at 311 columns where the other twelve are 39–91. Most of that
width is Cedar's provenance quartet per measured fact — `gaming_machines` ·
`_value_basis` · `_observation_status` · `_observed_date` — which is the
product's differentiator, and `770` rule 6 already forbids dropping columns
because it makes the schema depend on which rows shipped.

So `order_columns()` bands every dataset's header instead:

1. **identity** — `cedar_uid`, `cedar_place_id`, `tribe_id`, `entity_id`,
   `facility_id`, the contract's declared keys, then the names;
2. **substantive** — where it is, what it is, how big, whose;
3. **provenance** — `*_basis`, `*_observed_date`, `*_source_url`,
   `*_absent_reason`, `*_quote`;
4. **joined** — grouped by the table each column came from.

It is a **stable permutation that raises rather than lose or duplicate a
column**, applied to all thirteen. Gaming's first screen now runs
`cedar_uid, cedar_place_id, tribe_id, entity_id, facility_id, tribe,
facility_name, company, tribe_canonical_name, address, city, state,
postal_code, latitude, longitude, property_status, open_date, close_date,
gaming_machines, table_games, …`.

---

## 3. The gaming collection: what was wrong, and what is now right

`py -3 code/1141_gaming_quality_pass.py report | apply | verify | selftest`

### Referential integrity: clean before this pass

Measured across all 65 tables: **zero dangling `facility_id`, zero dangling
`cedar_place_id`, zero dangling `cedar_uid` or `tribe_id`.** Whatever else was
wrong, the collection's keys all resolve.

### Linkage fixed

| table | before | after | route |
|---|---:|---:|---|
| `gaming_project_facilities.cedar_uid` | 0 / 19 | **19 / 19** | Federal Register legal name, unique register-wide |
| `state_gaming_observations` keyed to a tribe | 348 / 494 | **440 / 494** | the four rules below |
| `gaming_property_site_observations` keyed to a tribe | 167 / 262 | **262 / 262** | facility_id 5, domain ledger 88, page text 2 |
| `gaming_properties.csv` rows | 784 | **787** | row conservation against `gaming_facilities.csv` |

### One root cause behind 92 of those links

`cedar_identity_register.csv` carries **two** names per entity, and the
state-observation matcher read only the first:

| handle | `canonical_name` | `federal_register_legal_name` |
|---|---|---|
| `TRBF-FSTCTY-00` | Forest County | Forest County Potawatomi Community, Wisconsin |
| `TRBF-SRMHWK-00` | Saint Regis | Saint Regis Mohawk Tribe |
| `TRBF-MOJAVE-00` | Fort Mojave | Fort Mojave Indian Tribe of Arizona, California & Nevada |
| `TRBF-ONDAWI-00` | Oneida Nation (Wisconsin) | |
| `TRBF-ONDANY-00` | Oneida | |

`canonical_name` is a **distinctive stem, not the entity's name.** Every
refusal the matcher recorded was answerable from the column beside the one it
read:

- **82 rows, Oneida, Wisconsin** — `refused_state_disagreement:spine=NY`. It
  found Oneida (NY), saw Wisconsin, and refused **without ever asking whether a
  Wisconsin candidate existed.** `Oneida Nation (Wisconsin)` was in the spine
  the whole time. *A state-disagreement refusal that never searched the
  observation's own state is not a refusal, it is a miss.*
- **8 rows, Potawatomi, Wisconsin** — `ambiguous_containment:3`, naming Citizen
  Potawatomi Nation (OK), its CDFI (OK) and Nottawaseppi (MI), and **not** the
  Forest County Potawatomi Community, whose canonical name is the two words
  `Forest County`. The ambiguity was manufactured by the right answer being
  invisible.
- **1 row, St. Regis Mohawk Tribe, New York** — `no_spine_match`. The spine
  says `Saint`. One abbreviation.
- **1 row, Fort Mojave Indian Tribe, Nevada** — `refused_state_disagreement:
  spine=CA`. The Avi Resort is in Laughlin NV; the entity's own Federal
  Register legal name reads *"of Arizona, California & Nevada"*. **The spine
  answered the objection in the field beside the one that raised it.** A
  reservation that crosses a state line has one register `state` and several
  states.

The matcher in `1141.resolve()` is deterministic and returns one answer or
none: three rules, each **scoped by state**, each requiring exactly one
candidate among `TRBF-` entities. Dropping generic tokens (`TRIBE`, `NATION`,
`BAND`, `OF`, `THE`) is only safe because of that scope, and the rule that
produced each link is written into `tribe_match_method` **appended to the
original refusal, not over it** — the refusal is the evidence the correction
was needed.

### What is deliberately still blank

**54 state-observation rows.** They are `applies_to = state` aggregates
(`net_win_state_aggregate`) and rows publishing no tribe name at all. Attaching
one to a nation would turn a statewide total into that nation's revenue.
`1141 verify` FAILS if any `applies_to = state` row is ever keyed to a tribe.

**2 of 787 gaming facility rows carry no `tribe_id`/`cedar_uid`**, and both are
correct: `VP-0109` is one of the 16 `NOT_A_PLACE` rows (`Konkow Valley Band -
no casino`), and `CEDAR-FAC-000020` carries `entity_match_basis = "BLANK BY
RULING"`. Across the 787 rows there are **284 distinct `tribe_id` and 284
distinct `cedar_uid`**, agreeing exactly; over the **717 distinct places** there
are **272 distinct operators and zero places whose rows disagree about the
operator.** The 12-entity gap is entities that appear only on negative
assertions — nations Cedar records as operating no gaming property.

### `n_revenue_bound_fiscal_years` is a ROW count and its name is not

It equals the number of `gaming_revenue_bounds.csv` rows joining the facility
on **787 of 787**, and the number of DISTINCT fiscal years on **732**. The 55
that diverge are the biggest properties — Foxwoods Resort Casino reads 82 where
the year count is 32, Mohegan Sun 79 against 29 — because one facility-year can
carry two bounds (a regional GGR ceiling and the same ceiling net of known
revenue are two rows, one year). The codebook hedges it as *"usually a year
count"*; usually is 93.0%, and the overstatement reaches 2.6x.

**The value is not changed.** It is an established column with documented
meaning and consumers on disk, and silently redefining it would be worse than
the misnomer. `n_revenue_bound_distinct_fiscal_years` is added beside it.

### The five HOLD_OPEN place groups

`review/place_gaming_hold_open_disposition_2026-09-02.csv`. `1129` emits one
verdict string, `HOLD_OPEN`, for two entirely different states of knowledge —
*these are genuinely two places* and *we cannot tell* — and a reader cannot
distinguish them. **Three of the five were never open questions**, and saying
so moves no count, because `1129` V9 already reconciles them as the reason the
adjudicated total is 717 rather than the mechanical 714.

| group | disposition | evidence |
|---|---|---|
| THREE RIVERS (OR) | **SETTLED_SEPARATE** | Not a casino-and-hotel pair at all: two casinos, one brand, **67 km apart**. ZIP 97420 at 43.3900,-124.2655, `company` = "Three Rivers Casino - Coos Bay"; ZIP 97439 at 43.9796,-124.0874, "Three Rivers Casino Resort - Florence" |
| GLACIER PEAKS (MT) | **SETTLED_SEPARATE** | Casino and its hotel at one site — identical ZIP+4 `59417-1450`, coordinates **6 m apart**, the closest pair in the sweep. Held apart by the standing casino-and-hotel rule, not by doubt |
| CITIES OF GOLD (NM) | **SETTLED_SEPARATE** | Same rule. **A separate defect found while checking it:** one street address, two coordinates **5.7 km apart** — `CCP-841600` at Pojoaque, `CCP-39300` toward Santa Fe with `coords_basis` "hand-curated". Logged, not repaired; a coordinate is evidence and replacing it needs a source |
| THE STABLES (OK) | **ESCALATE_OWNER** | The facts are settled: one property at 530 H Street SE, Miami OK, a genuine **Miami/Modoc joint operation** — Casino City's own row says "Modoc Tribe of Oklahoma/Miami Tribe of Oklahoma". What needs a ruling is that a `cedar_place_id` is a SUB-HUB of the entity that OPERATES the place, and this place has two |
| 7 CLANS FIRST COUNCIL (OK) | **ESCALATE_OWNER** | One property at 12875 N Highway 77, Newkirk OK, filed to two nations. Evidence points one way — the Otoe-Missouria Tribe's own casino listing names that exact address; the NIGC gaming location map lists the property there and Cedar links it at tier A; the other five 7 Clans rows are all Otoe-Missouria. Not applied because the wrong `tribe_id` has already propagated a **Ponca** tribal-state compact onto the property in `gaming_property_federal_traces.csv`, and repointing the display columns while leaving the derived traces is the Copper River defect exactly |

Either escalated ruling moves 717.

---

## 4. `1116 derive` was handing out a superseded number

The standing gate against stale figures — `py -3
code/1116_ruling_propagation_2026_09_02.py derive`, whose whole purpose is to
let a writer paste a fresh measurement instead of a memory — **derived 714 for
the gaming property denominator**, under a comment reading *"846's algorithm,
reproduced"*. It was, in the morning. `846::_denom` moved to
`COUNT(DISTINCT cedar_place_id)` = **717**; `1116` went on computing
`facility_rows − mechanical_duplicate_extras` from its own name-cluster
heuristic.

Two ladders for one number, and the second one drifted — which is exactly why
`248` is a retired stub pointing at `293`. `1116` now **reads** the place id and
prints the mechanical 714 only to explain why it is wrong.

**`714` is still quoted as "the property denominator" in seven other
documents**: `ARCHITECTURE_DECISIONS.md`, `CODEX_PR29_OPEN.md`,
`DEPENDENCY_MANIFEST.md`, `MONEY_TOTALLING_RULES.md` (×3),
`SEC_GAMING_FACILITY_REVENUE_BUILD_LOG.md`,
`TRIBAL_DEBT_HOLDINGS_BUILD_LOG.md`, `WHAT_IS_MISSING.md`. Most of them carry
the `GAMING-DENOMINATOR-2026-09-02` banner, and **the banner text itself is
what says 714**, so a doc-level rule in `1116` would be answered by the very
sentence that is wrong. Sweeping them is an integrator pass; the corrected
sentence is now what `1116 derive` prints.

---

## 5. Everything this pass found and did NOT fix

- **`gaming_facilities.company` is not a company.** It holds an alternate
  property name from the vendor vintage — identical to `facility_name` on 334
  rows, different on 109, blank on 344. Two of the 109 carry `?` where a
  non-ASCII character was lost (`Keex Kwan Gaming ? Bingo`, `Yaamava? Resort &
  Casino at San Manuel`) and `facility_name` has the right character on both.
  Renaming a shipped column is an owner decision.
- **`gaming_vendor_tribal_licenses` has a parser defect.** 145 of 740 rows have
  no `entity_id`, and the regulator strings say why: `Each TGA Gaming
  Commission`, `These Tribal Gaming Commission`, `Tribe's Tribal Gaming
  Commission`, `Indian Tribal Gaming Commission`. The extractor took whatever
  words preceded "Tribal Gaming Commission" out of running prose. About 60 name
  a real regulator (Gun Lake 35, Barona 12, San Manuel 7, San Carlos Apache 7)
  and are recoverable once the extractor is fixed; the rest are not entities.
- **`digital_gaming_revenue`'s 2,870 rows with no `tribe_id` are mostly
  correct, not a gap.** CT Lottery Corp (1,254), MGM Grand Detroit (385),
  MotorCity Casino (385), Greektown (385) are commercial operators in
  state-published series that also carry tribal licensees. One candidate is
  worth a look: `Seminole Hard Rock Digital` (AZ, 6 rows).
- **`wa_machine_transfers.csv` ships zero rows**, and it,
  `gaming_property_locations.csv`, `gaming_web_harvest_coverage.csv` and
  `gaming_web_harvest_observations.csv` are `UNDOCUMENTED` in
  `dataset_contracts.json` — an undeclared grain means `1137` will not fold
  them in.
- **`fac_audit_sefa_gaming_programs.csv` has one row.** Not investigated.
- **The Otoe-Missouria's own listing disagrees with Cedar on two addresses**:
  7 Clans Perry at "511 Kaw Street, Perry OK" against Cedar's "1101 W Doolin
  Ave", and 7 Clans Red Rock at "8401 Highway 177" against Cedar's "8402". Both
  are plausibly a relocation and a typo respectively; neither was changed.
- **`VP-0169 "7 Clans Ponca Casino"` (1664 N Hwy 177, Ponca City) is filed to
  the Ponca Tribe of Indians of Oklahoma, and the Otoe-Missouria's own casino
  listing names five properties and no Ponca City one.** Two searches did not
  settle whose it is. Flagged, unresolved.

---

## 6. Reproducing all of it

```
py -3 code/1141_gaming_quality_pass.py report     # measure, write nothing
py -3 code/1141_gaming_quality_pass.py apply
py -3 code/1141_gaming_quality_pass.py verify     # exits 1 if it did not land
py -3 code/1141_gaming_quality_pass.py selftest   # 3/3 detectors fire
py -3 code/1137_customer_dataset_combine.py build gaming
py -3 code/1137_customer_dataset_combine.py verify
py -3 code/1129_place_ids.py verify               # 16/16, denominator 717
py -3 code/cedar_publication.py verify            # 13 built, 12 storefront
```

**Every `1141` write is an in-place enricher.** A rebuild of
`gaming_project_facilities.csv`, `state_gaming_observations.csv`,
`gaming_property_site_observations.csv`, `gaming_properties.csv` or
`gaming_facilities.csv` reverts it. `1141 verify` is what tells you; re-run
`1141 apply` after any of those rebuilds, and re-run it LAST.
