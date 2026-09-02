# Codebook — the BIA's own ArcGIS registers

*Five tables, 1,119 rows. Acquired 2026-09-02 by
`code/1119_acquire_biamaps_arcgis.py` from `biamaps.geoplatform.gov`, the
Bureau of Indian Affairs' ArcGIS REST server. No API key; `robots.txt`
returns 404, so nothing is disallowed for any agent token this client
plausibly is — checked as a union over nine tokens, not with our own UA.*

*The sixth layer from the same host, the 249,165-row mineral acreage table,
has its own codebook: `12g_bia_mineral_acreage.md`. It is a natural-resources
table and is named `resource_*` so the entity layer does not claim it.*

Definitions below are taken from the values on disk. Every fill percentage
was counted on the full file.

---

## `bia_tribal_leaders_directory.csv` — 587 rows

One row per **entry** in the BIA Tribal Leaders Directory. **A nation with a
chair and a vice-chair is two rows.** Do not count rows as nations: 587 rows
carry 587 distinct `objectid` and fewer distinct nations.

This is the structured form of a source Cedar already reads — the registry
entry `bia_directory` reads the HTML directory — and it adds fields the HTML
does not carry.

| Variable | Type | Units / format | Filled | Description |
|---|---|---|---:|---|
| `objectid` | integer | server-assigned | 100% | The primary key, and **it is assigned by ArcGIS, not by the BIA**. Stable within a service edition only. Do not persist a join on it across a re-pull; use `retrieved_at` to know which edition you are holding. |
| `tribefullname` | text | text | 100% | The nation's full name as the BIA writes it. 508 of the 587 distinct values reach a Cedar spine entity by exact or token-set name match; the 79 that do not are largely FR-parenthetical variants (`…, California`) and cross-references (`Arctic Village (See Native Village of Venetie…)`). See `docs/NATIVE_ENTITY_NUANCES.md` before matching. |
| `tribe` | text | text | — | Short form. Not unique; never join on it. |
| `tribealternatename` | text | text | — | An alternate name the BIA records. A genuine alias source. |
| `tribalcomponent` | text | category | — | The BIA's own component label for a constituent band or village. |
| `jobtitle` | text | text | — | The person's role (`Chairman`, `President`, `Chairperson`). **Publishes.** |
| `biaregion` / `biaagency` | text | category | — | The BIA region and agency this nation sits under. The BIA's own answer, which is what makes this table an authority for `entity.bia_region` rather than an echo. |
| `dateelected` / `nextelection` | integer | epoch ms | — | ArcGIS epoch milliseconds. `*_iso` companions render them; **`0` renders as blank, not as 1970-01-01** — a sentinel that renders as a plausible date is worse than a blank. |
| `city`, `state`, `zipcode` | text | — | — | Office location. Publishes. |
| `website` | text | URL | — | The nation's own site. |
| `alaska` | text | flag | — | The publisher's Alaska marker. |
| `ancsaregion`, `blmregion`, `borregion`, `fwsregion`, `lcc`, `npsregion`, `usgsregion`, `alaskasubsistenceregion` | text | category | — | Seven other agencies' regional assignments for the same nation, published in one place. Nothing in Cedar holds this crosswalk. |
| `latitude`, `longtitude` | float | WGS84 | — | Publisher's spelling of `longtitude` kept as recorded. |

**HELD, NOT PUBLISHED** — a natural person's data apart from their public
role, per `docs/PUBLICATION_POLICY.md`: `firstname`, `lastname`,
`middlename`, `salutation`, `suffix`, `aka`, `email`, `phone`, `fax`,
`physicaladdress`, `mailingaddress`. The **role** (`jobtitle`) and the
**nation** publish; the person's contact details do not.

---

## `bia_aian_national_lar.csv` — 335 rows

One row per **Land Area Record**. The service's own description, verbatim:

> *the external extent of federal Indian reservations and the external extent
> of associated land held in "trust" by the United States, "restricted fee" or
> "mixed ownership" status*

| Variable | Type | Units / format | Filled | Description |
|---|---|---|---:|---|
| `LARID` | text | `LAR0002` | 100% | Primary key. 335 distinct, 0 blank. |
| `LARNAME` | text | text | 100% | **A LAND AREA name, not a tribe name.** `Allegany`, `Aquinnah`, `Annette Island`. Only 219 of 335 reach a spine entity by name and the 116 that do not are mostly correct — the land area and the nation are different things. **Never treat `LARNAME` as an entity name.** |
| `CLASSIFICATION` | text | category | 100% | The publisher's land-status code (`1`, `3`). The service does not publish a legend for it and one has not been invented here. |
| `GISACRES` | float | acres | 100% | **A GIS-computed polygon area, not a title acreage.** It is not the same measure as `acres` in the mineral acreage table and the two must never be differenced or reconciled against each other. |
| `REGION` | text | category | 100% | BIA region. |
| `Shape__Area`, `Shape__Length` | float | degrees² / degrees | 100% | Web-Mercator shape metrics. Not acres; not miles. |

Geometry was **not** taken (`returnGeometry=false`): Cedar has no spatial
consumer and `GISACRES` is an attribute.

---

## `bia_offices.csv` — 93 rows

One row per BIA office. The facility register.

> ### ⚠ `OFFICEID` IS NOT UNIQUE AND JOINING ON IT MERGES TWO AGENCIES
> 93 rows, **92 distinct `OFFICEID`**. `OFID0038` is carried by **both**
> `Salt River Agency` (OBJECTID 30) and `San Carlos Agency` (OBJECTID 31).
> That is a defect in the BIA's own register, not in the pull. It is recorded
> rather than repaired, because Cedar does not silently correct a publisher's
> identifier. **Key on `OBJECTID`.**

| Variable | Type | Filled | Description |
|---|---|---:|---|
| `OBJECTID` | integer | 100% | Primary key. Server-assigned; see the caveat above. |
| `OFFICEID` | text | 100% | **Not unique.** See the box. |
| `OFFICENAME` | text | 100% | e.g. `Northwest Regional Office`, `Salt River Agency`. |
| `OFFICETYPE` | text | 100% | `Agency`, `BIA Regional`, `BIA`. |
| `REGIONID` | text | 98% | Links an agency to its region. |
| `LATITUDE`, `LONGITUDE` | float | 100% | Office coordinates. |
| `PHONE` | text | 99% | The **office** switchboard. Publishes. |
| `FAX` | text | 85% | Office fax. |
| `URLADDRESS` | text | 100% | The office's page on `bia.gov`. |
| `REGION`, `AGENCY`, `CONTACTNAME`, `POCPREFIX`, `POCSUFFIX` | text | **0%** | **Columns that exist and are empty on every row.** Written as they were served so the absence is visible; a consumer must not read a blank here as "no region", only as "the register does not populate this column". |
| `ADDRESSID`, `POCEMAILADDRESS`, `POCMIDDLENAME` | text | 1–15% | **These carry the literal string `<Null>`, not a blank.** An `is null` test in SQL will not find them and a `== ""` test in Python will not either. |

**HELD, NOT PUBLISHED**: `POCFIRSTNAME`, `POCLASTNAME`, `POCMIDDLENAME`,
`POCEMAILADDRESS`, `CONTACTNAME`, `POCPREFIX`, `POCSUFFIX`. `POCJOBTITLE`
(e.g. `Regional Director`) is a role and publishes.

---

## `bia_pl102_477_plans.csv` — 84 rows

One row per **PL 102-477 self-governance plan agreement**. No Cedar source
covered this programme before.

The value here is the **dates**. `docs/STALE_TAIL_CLOSURE_1081.md` leaves a
545-entity tail with no dated public record, and the SBA DSBS extract already
on disk cannot close it because it carries no date column. These do.

| Variable | Type | Units / format | Filled | Description |
|---|---|---|---:|---|
| `objectid` | integer | server-assigned | 100% | Primary key. 84 distinct. |
| `partner_name` | text | text | 100% | The tribe or consortium holding the plan. **Not a key** — a partner with plans in two service areas appears twice. 73 of 84 reach a spine entity by name; the 11 that do not are consortia (`Tanana Chiefs Conference`, `Kawerak, Inc.`, `South Puget Intertribal Planning Agency`, `Central Council of Tlingit and Haida Indians of Alaska`), several of which the spine holds under a different name. |
| `organization_type` | text | category | 100% | `Tribe` or `Consortium`. This is the column that says a row is an aggregate. **An aggregate party must never resolve to one entity.** |
| `agreement_type` | text | category | 100% | `Self-Governance Compact Agreement` or `Self-Determination Contract`. |
| `plan_start_date` | integer | epoch ms | 100% | Plan start. `plan_start_date_iso` renders it (`2022-10-01`, `2025-10-01` …). |
| `plan_expiration_date` | integer | epoch ms | 100% | Plan expiry, with `_iso`. |
| `plan_renewal_date` | integer | epoch ms | 100% | Renewal date, with `_iso`. |
| `plan_service_area` | text | text | **13%** | Blank on 73 of 84 rows. Blank means the publisher did not state one. |
| `region` | text | category | 100% | BIA region. |
| `acronym` | text | text | 12% | Where the partner uses one. |
| `latitude`, `longitude` | float | WGS84 | 100% | Point location. |
| `title` | text | text | 100% | The signing leader's **role** (`Chairman`, `President`). Publishes. |

**HELD, NOT PUBLISHED**: `first_name`, `last_name` — the tribal leader who
signed, named apart from their role. **`email_bia_aotr` is NOT a personal
address**: it is `477PlanSubmission@bia.gov` on all 84 rows, a shared agency
mailbox, and it publishes.

---

## `bia_ofa_petitioners.csv` — 20 rows

One row per petitioner before the **Office of Federal Acknowledgment**.

> ### This is the NEGATIVE CASE, and it is the whole reason to hold it
> `docs/ASSERTION_LAYER.md` records, under *Where this is honestly weak*, that
> **`entity.is_federally_recognized` has no negative case.** A roster holding
> only positives cannot support any claim about the recognition boundary —
> there is nothing for a classifier, a coverage statement or a denominator to
> be wrong against.
>
> Measured: **4 of these 20 petitioners reach a Cedar spine entity by name;
> 16 do not.** That 16 is the point.

> ### What this table does NOT say
> Being on it means a group **petitioned**. The layer publishes no outcome
> column, so a consumer may write *"petitioned for federal acknowledgment and
> does not appear on the Federal Register roster"* and may **not** write
> *"was refused"*, *"was denied"* or *"is not a tribe"*. The distinction is
> the difference between a fact and a defamation.

| Variable | Type | Filled | Description |
|---|---|---:|---|
| `petition_number` | text | 100% | Primary key. OFA's own number, zero-padded (`005`, `032`, `056`). 20 distinct. |
| `petitioner_name` | text | 100% | The group's name as it petitioned. |
| `address`, `city`, `zipcode` | text | 100% | Contact address as published by OFA. This is an **organisation's** address, not a person's. |
| `state` | text | 100% | **Full state names (`California`, `Louisiana`, `New Mexico`), not USPS codes.** Any join to a Cedar table keyed on a two-letter state will silently match nothing. |
| `latitude`, `longitude` | float | 100% | Point location. |
| `website` | text | 100% | The OFA page for the petition on `bia.gov`. |

---

## Columns every one of these five tables carries

| Variable | Description |
|---|---|
| `source_url` | The exact FeatureServer layer the row came from. |
| `source_service_path` | The service folder and name, e.g. `BOGS/BIA_Office`. |
| `retrieved_at` | UTC timestamp of the pull. **`objectid` is only meaningful against this vintage.** |
| `source_id` | `bia_biamaps_arcgis`. |
| `population_basis` | `TYPE_FILTER` — the publisher's own register, taken whole. There is no identifier leg and none was available. |
| `inclusion_basis` | `program_authority` on all five tables (ADR-013 C12). These registers exist *only* for Indian Country by statute; no row needs a term match or an entity link to justify its presence. |
| `inclusion_basis_detail` | The specific authority, per table — e.g. *"Public Law 102-477 tribal self-governance plan agreements; the programme is available only to tribes and tribal consortia"*, *"petitioners before the Office of Federal Acknowledgment under 25 CFR Part 83"*. |

## Reproducing

```
py -3 code/1119_acquire_biamaps_arcgis.py probe    # counts + robots, cheap
py -3 code/1119_acquire_biamaps_arcgis.py pull
py -3 code/1119_acquire_biamaps_arcgis.py build    # zero network
py -3 code/1119_acquire_biamaps_arcgis.py verify   # exits 1 on breach
py -3 code/1119_acquire_biamaps_arcgis.py selftest # proves verify FIRES
```

Every page is hashed and every hash is in
`data/raw/external/biamaps/_manifest.json`; the row count of each table is
reconciled against a **fresh** `returnCountOnly` taken *after* the last page,
which is the check the FERC truncation incident earned.
