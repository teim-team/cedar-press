# The register-only tail — entities with no substantive Cedar row

*Generated 2026-09-02 by `code/1021_register_only_first_rows.py`. Evidence: `data/staging/register_only_first_rows.csv`. This is STAGING. Promoting any of it to a dataset is an assertion and goes through 510.*

## Why `830` reported zero

`code/830_entity_freshness.py` prints **"appear in NO Cedar row at all"** and on 2026-09-02 it printed **0**. That is not a finding, it is a defect of the familiar shape: the check measures something other than what its name says and therefore always reads green.

830 scans every id-bearing `*.csv` in `data/clean`. Four of those are the identity layer, not datasets — and one of them is **830's own output**. `cedar_entity_freshness.csv` holds one row per register entity and lives in the directory 830 scans, so from its second run onward every entity is "in a Cedar row" and the number is pinned at zero permanently.

| excluded here | why |
|---|---|
| `cedar_entity_freshness.csv` | 830's own output, one row per entity — the self-reference that pins the measure |
| `cedar_assertions.csv` | what Cedar has claimed about an entity |
| `cedar_resolved_facts.csv` | what Cedar has adjudicated |
| `entity_aliases.csv` | names, one or more for every entity |

Excluding the identity layer and any table that is a census of the register, **83** register entities have no row in any of the 140 substantive tables, and **31** more have exactly one.

The slice worked here is both — the thin tail, **114** entities. The line between the two groups moved while this was being written: the newsletter workstream landed `tribal_newsletter_corpus.csv` and 21 entities that had been register-only an hour earlier acquired one row apiece. Slicing on zero alone would have dropped them at the moment they became reachable. `n_substantive_tables` on every evidence row keeps the two states told apart.

## The 114 entities, by class

| entity class | in the thin tail | of those, in ZERO tables | given a first row here |
|---|---:|---:|---:|
| BIE School | 87 | 83 | 85 |
| Federal-level self-governance consortium | 18 | 0 | 18 |
| Native Community Development Financial Institution | 3 | 0 | 3 |
| Individually Native-owned business | 3 | 0 | 1 |
| Urban Indian Organization | 3 | 0 | 1 |
| **total** | **114** | **83** | **108** |

## What was found

| route | rows |
|---|---:|
| NCES_CCD | 85 |
| USASPENDING | 30 |
| IRS_990 | 21 |
| NONE | 6 |

## Named candidates, NOT resolved - 6

*Names that overlap but are not the same name. Overlap against the shorter name is what produced four wrong EINs on the first pass, so these are reported for a human rather than recorded as the entity's filing. No identifier is claimed on these rows.*

| entity | possible filer |
|---|---|
| Billings Urban Indian Health and Wellness Ce | EIN 27-4681721 South Billings Urban Renewal Association | Billings MT |
| Juel Fairbanks Recovery Services | EIN 41-0987441 Juel Fairbanks Aftercare Residence | St Paul MN |
| Laguna Creek LLC | EIN 41-2035448 Laguna Creek Gridiron Club | Elk Grove CA |
| Oklahoma City Indian Clinic | EIN 73-0955756 Central Oklahoma American Indian Health Council Inc | O |
| Southern Indian Health Council, Inc. | EIN 93-1216297 Southern Exposure | San Francisco CA |
| Tribal Energy Alternatives | EIN 26-3440182 Energy Alternatives For The 21st Century | Pelham NY |

## Checked, nothing located — 6

*Every one of these has a row in `register_only_first_rows.csv` naming the routes run and the date. That is a finding. It is not the same as unexamined, and the two must never be collapsed.*

| entity | class |
|---|---|
| Cherokee Central Middle School | BIE School |
| Shiprock Reservation Dormitory | BIE School |
| Tallsalt Advisors / Mette Associates | Individually Native-owned business |
| Laguna Creek LLC | Individually Native-owned business |
| Billings Urban Indian Health and Wellness Center | Urban Indian Organization |
| Juel Fairbanks Recovery Services | Urban Indian Organization |
