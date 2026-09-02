# Federal Indian Program Geography — build log

*Built 2026-08-06 by `code/85_build_admin_region_crosswalk.py`. Owns BIA, IHS
and HUD ONAP. NIGC is a separate agent's build and merges into the same files.*

---

## The rule this layer exists to enforce

**A tribe does not have one universal federal region.** It sits, at the same
moment, in a BIA region, a BIA agency, an IHS area, an IHS service unit, an
NIGC region and a HUD ONAP area — and those boundaries do not align.

There is therefore no `region` column anywhere in this layer. Every assignment
names the programme it belongs to, because the same word means different
ground in different programmes:

| "Phoenix" | means |
|---|---|
| **BIA** | not a region at all — Phoenix is where the **Western** Regional Office sits |
| **IHS** | the Phoenix Area: central Arizona, northern Nevada, north-western Utah; seven published service units |
| **NIGC** | a gaming-enforcement region with its own tribal roster *(other agent)* |
| **HUD** | the Phoenix **office** of the **Southwest** ONAP, which also operates from Albuquerque |

The measured version of the same point is in
`data/clean/admin_region_overlap_derived.csv`. BIA **Western** Region and IHS
**Phoenix** Area share 37 tribes — and IHS Phoenix also draws one tribe out of
BIA **Northwest**. BIA **Pacific** Region maps onto **Southwest** ONAP for 93
tribes. Those are co-occurrences computed from shared entities. **They are
never equivalencies**, the file says so on every row, and no agency has ever
mapped one system's boundaries onto another's.

---

## What was built

| File | Rows |
|---|---:|
| `data/clean/admin_region_systems.csv` | 6 systems (5 built, NIGC reserved) |
| `data/clean/admin_regions.csv` | 155 regions |
| `data/clean/admin_region_assignments.csv` | 2,124 assignments |
| `data/clean/admin_regional_observations.csv` | 27 region-level statistics |
| `data/clean/admin_region_overlap_derived.csv` | 28 derived pairs |
| `review/admin_region_unresolved.csv` | 363 held items |
| `data/raw/external/admin_regions/` | 95 raw files + `_SOURCE_MANIFEST.csv` |

### Regions per system, against the agency's own published count

| System | Built | Agency states | Reconciles? |
|---|---:|---|---|
| `BIA_REGION` | 12 | "twelve regional offices" — bia.gov/regional-offices | yes |
| `BIA_AGENCY` | 87 | "83 agencies" — same sentence | **no — see below** |
| `IHS_AREA` | 12 | 12 area links — ihs.gov/locations | yes |
| `IHS_SERVICE_UNIT` | 37 | no national count published | n/a — see below |
| `HUD_ONAP_AREA` | 7 | 7 areas across 8 office locations — hud.gov ONAP office list | yes |
| `NIGC_REGION` | **reserved** | — | populated by the NIGC build |

### Tribes assigned per system

| System | Distinct tribes |
|---|---:|
| `BIA_REGION` | 598 |
| `BIA_AGENCY` | 272 |
| `IHS_AREA` | 51 |
| `IHS_SERVICE_UNIT` | 0 |
| `HUD_ONAP_AREA` | 580 |

Plus 361 TDHE assignments across 148 distinct housing entities, 118
health-facility assignments and 10 Alaska tribal health organisations — each
kept as its own subject type, never folded into the tribe rows.

---

## Where the agency's own count disagreed with itself

### BIA: 83 declared, 87 agency-level offices published

`bia.gov/regional-offices` states in one sentence that programme delivery "is
administered by the twelve regional offices and 83 agencies." Walking all
twelve regional sites yields 87 agency-level offices. The gap is not a parsing
error; it is what BIA publishes:

- **80** are named "… Agency" — these are the agencies proper.
- **4** are field offices (New York Field Office, Shawnee Office, Juneau
  Office, Red Lake Agency/Field Office).
- **1** is the Wapato Irrigation Project, listed among Northwest's offices and
  not an agency.
- **2** are neither: the Great Plains Region lists the **Flandreau Santee
  Sioux Tribe** in its agency roster because the tribe delivers those services
  under a self-determination contract, and the Eastern Region lists its own
  **Regional Office** as a service point for 33 tribes with no agency between.

Every row carries `office_type=` in `notes`, so the roster can be counted
either way. **Neither number was adjusted to meet the other.**

Two further discoveries in the same pass:

- **The Southwest Region's agency page lives at a different slug.**
  `/regional-offices/southwest/agencies` 404s; BIA's own navigation points at
  `/regional-offices/southwest-region/agencies`. A 404 body from this CMS
  still contains a `<main>` element, so a build that trusted the file rather
  than the HTTP status would have produced a Southwest Region with zero
  agencies and said nothing. The fetch manifest records status per file and
  the build refuses any file that did not return 200.
- **Southwest publishes nine agencies and hyperlinks eight.** Laguna Agency is
  named in the sentence "Nine agencies are under the SWRO" and linked nowhere.
  It is carried with `verification_status=OFFICIAL_PROSE_ONLY`.

### Two BIA regions publish no agency list at all

Eastern's agencies page is prose; Southwest's is at the other slug. Their
agency rosters were recovered from the **tribes-served** pages, where each
agency heads its own list. Neither source alone is complete, so the roster is
the union of the two.

### One office, two official names

Western Region's `/papago-agency` is hyperlinked as **Tohono O'odham Agency**
and headed **Papago Agency** on the tribes-served page — the same office under
its new and old names. Keyed on the label alone this is two agencies; keyed on
the URL slug as well it is one row with an alias. The alias is recorded.

### IHS: service units are not published uniformly

Only **six** of the twelve areas publish anything they call a *Service Unit*
(Albuquerque 6, Billings 5, Great Plains 11, Nashville 4, Phoenix 7,
Portland 4 = 37). The rest publish facilities: Navajo says "There are 12
health care centers in the region", Oklahoma City and Tucson list clinics.
**Only entries IHS itself calls a Service Unit became `IHS_SERVICE_UNIT`
boundaries.** The other 65 entries are recorded as health facilities attached
to the *area* — real, sourced, and not promoted to a boundary the agency never
drew.

**Two areas publish no facilities page at all, and that is a fact about
delivery rather than a broken link.** Alaska Area care is delivered entirely by
tribal health organisations under P.L. 93-638 compacts, and California Area
entirely by tribally operated Indian health programmes. Neither runs IHS
service units. Both are recorded in the review queue as
`ihs_service_units_absent` with the reason, not as a gap.

### IHS: nine areas publish no tribe roster

Only Phoenix (tribes) and Alaska (tribal health organisations) publish a
roster of who they serve; Bemidji's "Tribal Information" page is about
consultation policy and lists nobody. **Tribes in the other nine areas
therefore carry no IHS assignment.** Bemidji publishes that it serves *34*
federally recognised tribes — that is a count, and it is stored as a regional
observation. Turning the count into a roster by picking 34 tribes out of the
five states it covers is exactly the move this layer forbids.

### HUD ONAP: seven areas, eight offices

The ONAP office list names Alaska, Eastern Woodlands, Hawaii, Northern Plains,
Northwest, Southern Plains and Southwest. **Southwest ONAP is one area
operating from two offices** (Phoenix and Albuquerque) and is one row, with
the second office in `notes`. Hawaii is the Native Hawaiian programmes office
and is kept distinct rather than merged into any mainland area.

HUD publishes, per area, a **Tribe/TDHE Assignments** list that labels each
name as either a *Tribe* or a *TDHE*. Those labels are preserved:
`subject_type` is `TRIBE` or `TDHE`, never a merged "recipient". A tribe and
its tribally designated housing entity are different legal persons, and which
one holds the grant is the fact the housing data turns on.

---

## Provenance and versioning

Every region and every assignment carries `source_url`, `fetched_date` and
`region_system_version`. The versions in this release are
`bia.gov-directory-2026`, `ihs.gov-directory-2026` and
`hud.gov-onap-offices-2026`; the HUD assignment lists additionally carry the
document date printed on the PDF (May 2025 for Northern Plains) in
`effective_start_year`.

**Administrative boundaries change, and none of this is valid backwards.**
Applying the 2026 structure to a 2013 grant, an archived facility list or a
superseded directory requires the then-current boundaries, which are not in
this release. `region_system_version` exists so a later reader can tell which
map a row was built from rather than assuming there is only one.

**Nothing is deleted for being out of date.** 99 assignments sit on subjects
that are not currently federally recognised entities and 542 are retained by
name where no Cedar entity resolved. An unlinked fact is still a fact; the
alternative is losing what an agency published because our spine has not
caught up with it.

---

## Quality checks — all pass

| Check | Result |
|---|---|
| Every federally recognised tribe has a reviewed BIA region | **577 / 577** |
| BIA agencies roll up to a valid BIA region | 87 / 87 |
| IHS service units roll up to a valid IHS area | 37 / 37 |
| Every assignment has a source | 2,124 / 2,124 |
| Inferred distinguishable from official | yes — `assignment_basis`, 0 rows inferred |
| Closed / non-current subjects retain assignments | 99 non-current + 542 unlinked, none dropped |
| Multiple assignments preserved, not overwritten | 89 subject × system pairs hold more than one region |
| No regional statistic mislabelled as entity-level | 27 observations, all region-keyed, **no entity key exists in the table** |
| Region IDs inside their system's block | 155 / 155 |

On the BIA region check: 598 tribes come from BIA's own tribes-served pages
(`OFFICIAL_AGENCY_ASSIGNMENT`, 330 rolled up from the agency that serves them,
57 served directly by a regional office). The remaining 269 come from the BIA
Tribal Leaders Directory region already on the entity spine — still BIA's own
attribute, but a **different publication**, so it is marked
`verification_status=OFFICIAL_SECONDARY_PUBLICATION` and `confidence=medium`
rather than being presented as the region's own roster. The two never blend.

### `assignment_basis` distribution

| Basis | Rows |
|---|---:|
| `OFFICIAL_AGENCY_ASSIGNMENT` | 930 |
| `PROGRAM_RECIPIENT_ASSIGNMENT` | 1,015 |
| `FACILITY_ASSIGNMENT` | 139 |
| `SERVICE_POPULATION` | 40 |
| `GEOGRAPHIC_INFERENCE` | **0** |

Nothing in this release was placed in a region by inference. Where an agency
did not publish an assignment, the entity has none.

---

## The observations table, and why it has no entity key

`admin_regional_observations.csv` holds statistics that exist only at region
level: the Pacific Region's 105 federally recognised tribes, the Eastern
Region's 460,980 trust acres and 102,677 restricted acres, Bemidji Area's 34
tribes and 11 Title V compacts, Phoenix Area's eleven service units.

**Those numbers describe the region.** Copying one onto each tribe or property
inside it manufactures an entity-level observation that nobody measured, and
that is the central failure this whole layer exists to prevent. The table is
deliberately separate, carries no `subject_id`, `tribe_id` or `entity_id`
column, and the QA pass asserts that no such column has appeared.

`published_at_region_level` separates the two directions:

- **15 rows, `=1`** — the agency published the figure for the region.
- **12 rows, `=0`** — Cedar Press aggregated it **upward** from entity rows
  (HUD ONAP award dollars and row counts). Aggregating entity rows up to a
  region is safe. Dividing a regional figure back down is not, and a `=0` row
  is a sum of what we hold, never a census of the region.

---

## Held for Elijah — `review/admin_region_unresolved.csv` (363 items)

| Item type | Count | What it is |
|---|---:|---|
| `ihs_facility` | 118 | facilities on the IHS locations map whose entry carries no area-bearing URL; the map groups them visually but publishes no area statement |
| `hud_onap_tribe` | 63 | names on a HUD ONAP roster that resolve to no Cedar entity — mostly Alaska villages and regional associations (`Chignik Native`, `Lime Village`, `Naqsragmuit Tribal Council`) that the resolver found ambiguous |
| `hud_onap_tdhe` | 148 | **every** TDHE HUD names. The entity spine holds no tribally designated housing entity, so each one is a candidate spine addition — see the note below |
| `bia_tribes_served` | 13 | tribe names on BIA rosters the resolver refused, e.g. `Fort Peck Tribal Executive Board`, `Winnemucca Paiute and Shoshone Tribe`, `Cedar Band` |
| `ihs_native_entity_roster` | 10 | Alaska tribal health organisations not on the spine |
| `ihs_tribe_roster` | 6 | IHS roster names the resolver refused |
| `region_headquarters_missing` | 3 | IHS Albuquerque, California and Tucson publish no street address on their own pages |
| `ihs_service_units_absent` | 2 | Alaska and California areas run no IHS service units |

Every one of these is a refusal, not a failure. `resolve_entity` from
`code/33_apply_party_rulings.py` is the only matcher used anywhere in this
build; no name matcher was written for it, and an unmatched name is reported
rather than guessed.

### Why every TDHE is unlinked, deliberately

**A TDHE is not its tribe.** The entity spine holds no tribally designated
housing entity — the only three rows mentioning housing are an intertribal
council and two CDFIs — so every TDHE name that "resolved" resolved by
containment onto the tribal government whose name it carries. `Blackfeet
Housing Program` landed on the Blackfeet Tribe, which asserts that the grantee
and the government are one legal person. That is precisely the collapse HUD's
own list is careful to avoid, and it would corrupt any later question about
who received a housing grant.

So TDHE rows keep the published name, take **no** `subject_id`, carry
`verification_status=OFFICIAL_UNLINKED`, and every distinct name is queued.
The tribe HUD prints the TDHE beneath is preserved in
`related_subject_name`, so the relationship survives without the identity
claim — and a regional authority such as AVCP RHA keeps one row per village it
administers rather than flattening to a single row that loses which
communities it covers. 361 TDHE assignment rows, 148 distinct entities.

---

## Interface for the NIGC build

The shared column contract is present on every row this script writes:
`administrative_region_id`, `region_system_code`, `region_system_version`,
`effective_start_year`, `effective_end_year`, `assignment_method`,
`confidence`, `source_url`, `fetched_date`.

**ID block reserved for NIGC: `CEDAR-ADMREG-300001` … `CEDAR-ADMREG-309999`.**
Script 85 never allocates inside it. Blocks are contiguous and
non-overlapping:

| System | Block |
|---|---|
| `BIA_REGION` | 100001–109999 |
| `BIA_AGENCY` | 110001–119999 |
| `IHS_AREA` | 200001–209999 |
| `IHS_SERVICE_UNIT` | 210001–219999 |
| **`NIGC_REGION`** | **300001–309999 — reserved** |
| `HUD_ONAP_AREA` | 400001–409999 |

Re-running `85 build` is safe alongside the NIGC build: it reads the three
shared CSVs back, keeps every row whose `region_system_code` is not one of the
five it owns, and rewrites only its own. `admin_region_systems.csv` carries a
placeholder `NIGC_REGION` row that a populated one supersedes.

---

## Reproducing

```
py -3 code/85_build_admin_region_crosswalk.py fetch   # 95 requests, ~2 min
py -3 code/85_build_admin_region_crosswalk.py build
py -3 code/41_build_codebooks.py                      # dataset 13_admin_regions
```

`fetch` is one sequential poller with a fixed delay across three hosts and no
retry loop, per `docs/PULL_DISCIPLINE.md`. All 95 requests returned 200 on the
2026-08-06 run. Raw copies live under `data/raw/external/admin_regions/` with
`_SOURCE_MANIFEST.csv` recording url, status, bytes and fetch date per file —
Cedar Press is self-contained and the build never depends on a live host.

`code/01_build_entity_spine.py` was **not** run; a rebuild drops appended
entities.
