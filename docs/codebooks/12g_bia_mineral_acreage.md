# Codebook — BIA mineral acreage tracts

*249,165 rows. Acquired 2026-09-02 by `code/1119_acquire_biamaps_arcgis.py`
from `biamaps.geoplatform.gov/server/rest/services/Hosted/BIA_Mineral_Acreage_Table`.
Definitions taken from the values on disk; every figure below was counted on
the full file.*

**One row per TITLE RECORD in the BIA Land Titles and Records offices'
mineral acreage report.** Not one row per tract, not one row per tribe, not
one row per reservation.

## Why Cedar holds it

`docs/WHAT_IS_MISSING.md`, natural-resources gap **#3**: *"no volume, no
price — revenue with no denominator."* `resource_revenue.csv` is 87%
aggregate-suppressed by statute, so a per-entity revenue figure mostly cannot
be published and, where it can, there has never been anything to divide it
by. This is the closest thing to a base the dataset can get: the acreage,
per tract, from the agency that holds the title.

It is **not** a revenue table and it must never be joined to one as though a
tract were a producing well.

---

> ## ⚠ THE TOTALLING RULE, MEASURED
>
> **Summing the `acres` column across rows overstates the acreage by
> 417,504.8 acres — 0.60%.**
>
> | | acres |
> |---|---:|
> | naive sum of all 249,165 rows | **70,290,363.9** |
> | one acreage per (`land_area_code`, `tract_id`) | **69,872,859.0** |
> | overstatement | **417,504.8 (0.60%)** |
>
> **Why:** 5,465 tracts appear **twice** — once with `ownership_type = Trust`
> and once with `ownership_type = Restricted` — and **both rows carry the
> identical acreage**, not a split of it. Tract `256 2181` on TURTLE MOUNTAIN
> is 157.08 acres and is written as 157.08 Trust *and* 157.08 Restricted.
> The rows are two title statuses recorded against one parcel, not two
> parcels.
>
> Concentrated, not spread: **FORT HALL alone accounts for 172,026 of the
> 417,505** overstated acres, then BAD RIVER (LA POINTE) 26,022, LAC COURTE
> OREILLES 20,002, PINE RIDGE 19,910, STANDING ROCK 17,909, OSAGE 14,588. A
> per-reservation figure for those six is wrong by a **large** margin, not by
> a rounding error.
>
> **Rule: take one acreage per (`land_area_code`, `tract_id`) before you
> total anything.** If you need the trust/restricted split, you are asking a
> different question and this column cannot answer it — the file states which
> statuses touch a tract, not how many acres each holds.
>
> Fenced in `docs/MONEY_TOTALLING_RULES.md` under
> `<!-- BEGIN ACQUIRE-BIA-ACREAGE -->`.

> ## ⚠ AND A PER-STATE TOTAL DOUBLE-COUNTS A CROSS-STATE TRACT
> `FORT MOJAVE 604 T 106`, 879.87 acres, is recorded **once under AZ and once
> under CA**, because the reservation straddles the state line. Every
> published attribute on the two rows is identical except `state`. Total by
> `land_area_code`; total by `state` only after deciding what a state
> boundary means for a tract that crosses one.

---

## Variables

| Variable | Type | Units / format | Filled | Description |
|---|---|---|---:|---|
| `objectid` | integer | server-assigned | 100% | **The only primary key.** 249,165 distinct, 0 blank. It is assigned by ArcGIS, not by the BIA, and is stable only within a service edition — this is `293`'s class 7 (a non-deterministic key) and it is declared, not hidden. Use `retrieved_at` to know which edition you hold; do not persist a join on `objectid` across a re-pull. |
| `ltro_code` | text | category | 100% | The Land Titles and Records Office of record: `A-ABERDEEN, SD` 66,137 · `C-BILLINGS, MT` 46,119 · `P-PORTLAND, OR` 40,868 · `G-MUSKOGEE, OK` 24,088 · `M-SOUTHWEST` 22,431 · `E-ANCHORAGE, AK` 17,299 · `F-MIDWEST LTRO` 14,328 · `B-ANADARKO, OK` 13,007 · `J-SACRAMENTO, CA` 4,888. **Nine values.** |
| `regional_office` | text | category | 100% | The BIA regional office, **twelve** values. **`ltro_code` and `regional_office` are not the same partition** — `M-SOUTHWEST` (one LTRO) spans the Western, Southwest and Navajo regional offices. Group by one or the other and say which. |
| `land_area_code` | text | numeric string | 100% | 494 distinct. The BIA's land-area identifier and the right grouping key. |
| `land_area_name` | text | text | 100% | 495 distinct. **A LAND AREA name, not a tribe name**: `AHPEATONE - OK`, `ALBUQUERQUE INDIAN SCHOOL - NM`, `ALEUT`, `TURTLE MOUNTAIN PD (FT PECK - ND)`. Only **184 of 495 reach a Cedar spine entity** by exact or token-set name match. **The acreage denominator does not arrive with a tribe key**, and building one is an adjudication, not a string match. |
| | | | | ⚠ Two `land_area_code`s carry a **leaked internal key** in place of a name: `982` → `E\|E\|01\|982` (elsewhere `SEALASKA`) and `183` → `P\|P\|04\|183` (elsewhere `KOOTENAI`). Treat a pipe-delimited `land_area_name` as missing. |
| `tract_id` | text | text | 100% | The tract number as LTRO writes it (`340 131 5`, `604 T 106`). Unique only within a `land_area_code`, and **not even then**: three tracts carry two different acreages under one number (CHEYENNE RIVER `340 131 5` at 160 and 479.69; ROSEBUD `345 100 5` at 160 and 320; ROSEBUD `345 513 5` at 95.7 and 160). Those are two title records on one tract number and collapsing them destroys acreage. |
| `acres` | float | acres | 100% | Acreage of the title record. 0 unparseable values across all 249,165 rows. **Read the totalling rule above before summing.** |
| `resource_code` | text | category | 100% | Which estate the record covers: `Both (Mineral and Surface)` 116,174 · `Minerals Only` 66,735 · `Surface Only` 52,784 · `Both (Except O & G)` 9,444 · `Coal` 1,887 · `All Minerals (Except Coal)` 1,173 · `See Note` 497 · `Both (Except Coal)` 393 · `All Minerals (Except O&G)` 64 · `Oil (Only)` 6 · `All Other Mineral (Except Oil)` 5 · `Sand and Gravel` 3. **Split-estate is normal here**: only 2 tracts in the whole file appear under more than one `resource_code`, so this is not a double-count risk — it is a description of what is owned. |
| | | | | ⚠ `See Note` (497 rows) is a pointer to a note the service does not publish. It is not a resource type; exclude it from any resource breakdown rather than bucketing it. |
| `ownership_type` | text | category | 100% | `Trust` 210,160 · `Restricted` 38,998 · `Unknown` 5 · `Both Trust & Restricted` 2. **This is the column behind the 0.60% overstatement** — see the box. Note the publisher itself uses `Both Trust & Restricted` on 2 rows, which is what the 5,465 two-row tracts would have been had it been used consistently. |
| `state` | text | USPS code | 100% | 39 states. `SD` 46,153 · `MT` 44,546 · `OK` 35,171 · `WA` 22,624 · `ND` 18,115 · `AK` 17,616 · `AZ` 10,754 · `ID` 9,525. See the cross-state box. |
| `inactivated_date` | integer | epoch ms | 100% | **`0` on every one of the 249,165 rows.** The column is served and is entirely unpopulated. `inactivated_date_iso` therefore renders **blank on every row, deliberately**: rendering `0` as `1970-01-01` would have put a real-looking date on the largest table Cedar holds, and a filter for "inactivated before 2000" would have returned the whole file. A sentinel that renders as a plausible value is worse than a blank. |
| `inactivated_date_iso` | text | YYYY-MM-DD | 0% | See above. Blank means "the source did not state one". |
| `source_url` · `source_service_path` · `retrieved_at` · `source_id` · `population_basis` | text | — | 100% | Provenance. `source_id = bia_biamaps_arcgis`; `population_basis = TYPE_FILTER` (the publisher's own register, taken whole — there is no identifier leg and none was available). |
| `inclusion_basis` | text | ADR-013 C12 | 100% | `program_authority`. Every row is Indian trust or restricted-fee title; the register exists for no other kind of land. |
| `inclusion_basis_detail` | text | text | 100% | *"Indian trust and restricted-fee mineral title held by the United States; the register exists only for Indian land (25 U.S.C. land titles and records)"*. |

---

## Reading it

**This is a title record, not a lease and not a well.** A tract with
`resource_code = Minerals Only` is a mineral estate held in trust; nothing
here says it is producing, leased, or generating a royalty. Joining it to
`resource_revenue.csv` as though a tract were a revenue unit is the error the
table exists to prevent, not to enable.

**It has no tribe key.** 184 of 495 land-area names reach the spine by name.
The remaining 311 include boarding-school lands, Alaska Native corporation
areas, public-domain allotments named for individuals (`AHPEATONE - OK`), and
land areas that genuinely belong to no single nation. **Do not manufacture
the link with a name matcher** — `docs/AGENT_FIELD_GUIDE.md` records what a
place-name collision costs, and `START_HERE.md` standing rule 1 records that
the exactness of a key says nothing about the correctness of a link.
Linking land areas to entities is an open task; it is named in
`docs/BIAMAPS_ACQUISITION_LOG_2026-09-02.md`.

**Alaska is 17,616 rows and 7.1% of the file.** Anyone scoping to the lower
48 must filter it out explicitly; the table does not do it for you.
