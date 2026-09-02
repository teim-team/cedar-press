# Codebook — Admin Regions

*2,340 rows across 5 file(s). Generated 2026-08-07.*

Variables marked **internal** are retained for auditing and are not included in published extracts.

| Variable | Type | Units / format | Filled | Description |
|---|---|---|---:|---|
| `region_system_code` | text | categorical | 100% | WHICH FEDERAL PROGRAMME'S GEOGRAPHY A ROW BELONGS TO, and the column to read before comparing any two regions. `BIA_REGION`, `BIA_AGENCY`, `IHS_AREA`, `IHS_SERVICE_UNIT`, `NIGC_REGION`, `HUD_ONAP_AREA`. A tribe sits in several of these at once and their boundaries do not align, so there is no universal region. The same word can name different ground in different systems - `Phoenix` is an IHS area, an NIGC region and a HUD office location, and is not a BIA region at all. |
| `agency` | text | text | 100% | Awarding agency. |
| `system_name` | text | text | 100% | Name. |
| `level` | text |  | 100% | One of: `1 - region`, `1 - area`, `2 - agency`, `2 - service unit` |
| `parent_system_code` | text | code | 33% | Classification code. |
| `region_system_version` | text | text | 100% | The published edition of the boundary set a row was built from, with the effective years it governs. Administrative boundaries change; a current structure is not valid for an earlier grant, directory or facility list. |
| `n_regions_built` | integer | count | 100% | Number of region rows this release holds for the system. |
| `agency_declared_count` | text | text | 67% | The count of regions the agency states in its own directory. Recorded separately from the count actually built so a discrepancy stays visible instead of being reconciled away. |
| `id_block_start` | text | code | 100% | First identifier reserved for the system. Blocks are contiguous and non-overlapping. |
| `id_block_end` | text | code | 100% | Last identifier reserved for the system. |
| `effective_start_year` | integer | YYYY | 48% | Year. |
| `effective_end_year` | empty | YYYY | 0% | Year. |
| `owned_by` | text |  | 100% | One of: `85_build_admin_region_crosswalk.py`, `NIGC build (separate script)` |
| `description` | text | text | 100% | Description of the item. |
| `source_url` | text | URL | 100% | Link to the record's published source. |
| `fetched_date` | text | YYYY-MM-DD | 100% | Date. |
| `built_date` | text | YYYY-MM-DD | 100% | Date. |
| `administrative_region_id` | text | code | 100% | Cedar Press identifier for one administrative region, area, agency or service unit. Stable across releases. The identifier belongs to exactly one programme system, so it can never be reused to mean a region of a different agency. |
| `region_code` | text | code | 100% | Short code for the region within its system. Unique only inside a `region_system_code`, never across systems. |
| `canonical_name` | text | text | 100% | Cedar Press standard name for the Native entity. |
| `official_name` | text | text | 100% | The office's full name as the agency itself publishes it. |
| `parent_administrative_region_id` | text | code | 80% | The region one level up, where the system has levels. BIA agencies sit under BIA regions and IHS service units under IHS areas. SYSTEMS HAVE DIFFERENT NUMBERS OF LEVELS and the hierarchy is not uniform; blank means the row is already top level. |
| `headquarters_city` | text | text | 18% | City the office operates from. |
| `headquarters_state` | text | code | 18% | State of the office, two-letter. |
| `effective_start_date` | empty | YYYY-MM-DD | 0% | Date. |
| `effective_end_date` | empty | YYYY-MM-DD | 0% | Date. |
| `active_status` | text | categorical | 100% | Whether the region is currently in operation. |
| `verification_status` | text |  | 100% | One of: `OFFICIAL_PUBLISHED`, `OFFICIAL_UNLINKED`, `OFFICIAL_SECONDARY_PUBLICATION`, `OFFICIAL_PROSE_ONLY` |
| `notes` | text | text | 96% | Analyst notes on the record. |
| `built_by_script` | text |  | 100% | One of: `85_build_admin_region_crosswalk.py` |
| `assignment_id` | text | code | 100% | Identifier for one assignment of one subject to one region. |
| `subject_type` | text | categorical | 100% | What kind of thing is being assigned: `TRIBE`, `NATIVE_ENTITY`, `GAMING_PROPERTY`, `HEALTH_FACILITY`, `TDHE`, `RESERVATION`, `PROJECT`, `PROGRAM_RECIPIENT`. A tribe and its tribally designated housing entity are different legal persons and appear as different subjects, never merged. |
| `subject_id` | text | code | 74% | The Cedar entity the assignment attaches to. BLANK MEANS THE AGENCY PUBLISHED A NAME THAT RESOLVES TO NO CEDAR ENTITY - the assignment is real and retained under `subject_name`, and no entity link is invented for it. |
| `subject_name` | text | text | 100% | The subject as the source names it. |
| `related_subject_name` | text | text | 17% | The other party the source pairs this subject with in the same listing - for a tribally designated housing entity, the tribe HUD lists it under. A regional housing authority serving many villages therefore keeps one row per community rather than collapsing to one, and the tribe and the TDHE stay separate subjects throughout. |
| `assignment_basis` | text | categorical | 100% | WHAT KIND OF EVIDENCE PUTS THIS SUBJECT IN THIS REGION, and the column to read before treating an assignment as authoritative. `OFFICIAL_AGENCY_ASSIGNMENT` - the administering agency published that this entity belongs to this office. `PROPERTY_LOCATION` - where a property physically sits. `FACILITY_ASSIGNMENT` - a facility the agency lists under the region. `SERVICE_POPULATION` - the agency names the entity among those it serves. `PROGRAM_RECIPIENT_ASSIGNMENT` - the entity receives a programme the office administers. `GEOGRAPHIC_INFERENCE` - derived from location, not published by the agency. `HISTORICAL_SOURCE` - from a superseded directory. AN OFFICIAL AGENCY ASSIGNMENT ALWAYS OUTRANKS A GEOGRAPHIC INFERENCE and the two are never merged. |
| `is_primary` | integer | 0/1 | 100% | 1 where the source presents this as the subject's assignment in that system. MORE THAN ONE ASSIGNMENT PER SYSTEM IS LEGITIMATE - a tribe can relate to several IHS facilities or service units - so this flag ranks assignments and never reduces them to one. |
| `confidence` | text |  | 100% | One of: `high`, `medium` |
| `assignment_method` *(internal)* | text |  | 100% |  |
| `observation_id` | text | code | 100% | Identifier for one statistic measured at region level. |
| `observation_name` | text | text | 100% | What the statistic counts or measures. |
| `observation_value` | integer | number | 100% | The value as published. |
| `observation_unit` | text | text | 100% | Unit of the value - `count`, `acres`, `persons`, `usd`. |
| `observation_year` | integer | YYYY | 56% | Year the statistic describes. Blank where the source states none. |
| `published_at_region_level` | integer | 0/1 | 100% | 1 where the agency itself published the figure for the region as a whole; 0 where Cedar Press aggregated it upward from entity rows. EITHER WAY THE VALUE DESCRIBES THE REGION AND NOT ITS MEMBERS. Copying a regional figure onto each tribe or property inside the region manufactures an entity-level observation that nobody measured, which is why this table carries no entity key. |
| `observation_basis` | text | categorical | 100% | Where the figure came from: `AGENCY_PUBLISHED` or `CEDAR_AGGREGATION_FROM_ENTITY_ROWS`. An aggregated figure is a sum of the rows Cedar Press holds, not a census of the region. |
| `source_quote` | text | text | 56% | The sentence in the cited source that establishes this region record, quoted so the claim can be checked without re-retrieving the source. |
| `system_a` | text |  | 100% | One of: `BIA_REGION`, `IHS_AREA` |
| `administrative_region_id_a` | text | code | 100% | The region on the first side of a derived cross-system pair. |
| `region_name_a` | text | text | 100% | Name of the first region in the pair. |
| `system_b` | text |  | 100% | One of: `HUD_ONAP_AREA`, `IHS_AREA` |
| `administrative_region_id_b` | text | code | 100% | The region on the second side of a derived cross-system pair. |
| `region_name_b` | text | text | 100% | Name of the second region in the pair. |
| `n_shared_tribes` | integer | count | 100% | How many tribes hold an assignment in both regions of the pair. |
| `relationship` | text | categorical | 100% | Whether the party OWNS the interest (`parent_native_entity`) or merely SERVES it (`serves_native_entities`), or is an outside `counterparty`. Ownership and service are different facts and collapsing them manufactures ownership. |
| `warning` | text |  | 100% | One of: `Derived from tribes both systems happen to share. NOT an official equivalency; the two agencies never mapped these boundaries onto each other.` |

## Value sets

- **`region_system_code`** — `HUD_ONAP_AREA`, `BIA_REGION`, `BIA_AGENCY`, `IHS_AREA`, `IHS_SERVICE_UNIT`, `NIGC_REGION`
- **`agency`** — `Bureau of Indian Affairs`, `Indian Health Service`, `National Indian Gaming Commission`, `Department of Housing and Urban Development`
- **`system_name`** — `BIA Regional Office`, `BIA Agency / Field Office`, `IHS Area`, `IHS Service Unit`, `NIGC Region`, `ONAP Area Office`
- **`level`** — `1 - region`, `1 - area`, `2 - agency`, `2 - service unit`
- **`parent_system_code`** — `BIA_REGION`, `IHS_AREA`
- **`region_system_version`** — `bia.gov-directory-2026`, `hud.gov-onap-offices-2026`, `ihs.gov-directory-2026`, `reserved`
- **`agency_declared_count`** — `twelve`, `83`, `12`, `7 areas / 8 office locations`
- **`id_block_start`** — `CEDAR-ADMREG-100001`, `CEDAR-ADMREG-110001`, `CEDAR-ADMREG-200001`, `CEDAR-ADMREG-210001`, `CEDAR-ADMREG-300001`, `CEDAR-ADMREG-400001`
- **`id_block_end`** — `CEDAR-ADMREG-109999`, `CEDAR-ADMREG-119999`, `CEDAR-ADMREG-209999`, `CEDAR-ADMREG-219999`, `CEDAR-ADMREG-309999`, `CEDAR-ADMREG-409999`
- **`owned_by`** — `85_build_admin_region_crosswalk.py`, `NIGC build (separate script)`
- **`description`** — `Twelve regional offices that administer BIA programme delivery to federally recognised tribes.`, `Reservation-level BIA offices reporting to a regional office. Often the more useful unit than the region for reservation-level records.`, `Twelve IHS areas. Drawn for health-service delivery and NOT coterminous with BIA regions.`, `Sub-area units of health-service delivery. IHS publishes them per area alongside tribally operated programmes; only entries IHS itself calls a Service Unit are recorded here.`, `NIGC gaming-enforcement regions. RESERVED - populated by the NIGC build, not by script 85. NIGC 'Phoenix' is not BIA 'Western' and not IHS 'Phoenix'.`, `Office of Native American Programs area offices. Assignments attach to the actual programme recipient - a tribe, a TDHE or a housing authority - which are different legal persons.`
- **`parent_administrative_region_id`** — `CEDAR-ADMREG-100007`, `CEDAR-ADMREG-100004`, `CEDAR-ADMREG-100012`, `CEDAR-ADMREG-200006`, `CEDAR-ADMREG-100011`, `CEDAR-ADMREG-100009`, `CEDAR-ADMREG-200010`, `CEDAR-ADMREG-100003`, `CEDAR-ADMREG-100006`, `CEDAR-ADMREG-200002`, `CEDAR-ADMREG-100010`, `CEDAR-ADMREG-200004`, `CEDAR-ADMREG-100002`, `CEDAR-ADMREG-100005`, `CEDAR-ADMREG-100008`, `CEDAR-ADMREG-200007`, `CEDAR-ADMREG-200011`, `CEDAR-ADMREG-100001`
- **`headquarters_city`** — `Anchorage`, `Phoenix`, `Nashville`, `Aberdeen`, `Portland`, `Billings`, `Oklahoma City`, `Muskogee`, `Bloomington`, `Gallup`, `Sacramento`, `Anadarko`, `Albuquerque`, `Bemidji`, `Window Rock`, `Chicago`, `Honolulu`, `Denver`, `Seattle`
- **`headquarters_state`** — `OK`, `AZ`, `AK`, `TN`, `SD`, `MN`, `NM`, `OR`, `MT`, `CA`, `IL`, `HI`, `CO`, `WA`
- **`verification_status`** — `OFFICIAL_PUBLISHED`, `OFFICIAL_UNLINKED`, `OFFICIAL_SECONDARY_PUBLICATION`, `OFFICIAL_PROSE_ONLY`
- **`subject_type`** — `TRIBE`, `TDHE`, `HEALTH_FACILITY`, `NATIVE_ENTITY`
- **`assignment_basis`** — `PROGRAM_RECIPIENT_ASSIGNMENT`, `OFFICIAL_AGENCY_ASSIGNMENT`, `FACILITY_ASSIGNMENT`, `SERVICE_POPULATION`
- **`confidence`** — `high`, `medium`
- **`observation_name`** — `federally_recognized_tribes_served`, `cedar_hud_onap_award_dollars`, `cedar_hud_onap_award_rows`, `title_i_contracts`, `urban_indian_health_programs`, `tribal_members_minimum`, `trust_acres`, `restricted_acres`, `land_area_million_acres_minimum`, `title_v_compacts`
- **`observation_unit`** — `count`, `usd`, `acres`, `persons`, `million_acres`
- **`observation_basis`** — `AGENCY_PUBLISHED`, `CEDAR_AGGREGATION_FROM_ENTITY_ROWS`
- **`source_quote`** — `e Region encompasses a dynamic and diverse mix of Tribes and natural resources. There are over 62,000 Tribal Members that make up the 34 Tribes under the Eastern Region’s jurisdiction. The service area incl`, `make up the 34 Tribes under the Eastern Region’s jurisdiction. The service area includes 460,980 acres held in trust, and 102,677 acres of restricted lands. The Eastern Region’s jurisdictional area consists`, `Eastern Region’s jurisdiction. The service area includes 460,980 acres held in trust, and 102,677 acres of restricted lands. The Eastern Region’s jurisdictional area consists of the states from Maine to Florida ov`, `s home to an impressive diversity of Tribes, with over 62,000 Tribal Members representing 34 unique Tribes. Our service area spans 460,980 acres held in trust and 102,677 acres of restricted lands`, `ved Agencies Contact Us Overview The BIA Great Plains Region provides funding and support to 16 federally recognized Indian tribes located in the states of North Dakota, South Dakota, and Nebraska. Tribes in this region`, `n the states of North Dakota, South Dakota, and Nebraska. Tribes in this region encompass over 6 million acres. The Region’s tribes have sustained various programs that the federal government traditio`, `s Overview The Bureau of Indian Affairs (BIA) Midwest Region provides funding and support to 36 federally recognized Indian tribes located in the states of Minnesota, Wisconsin, Michigan and Iowa. Tribes in the Midwest R`, `, with the responsibility of working toward strengthening intergovernmental assistance to the 105 federally recognized tribes in the Region’s service area, and improving interagency and intergovernmental cooperation`, `The Alaska Tribal Health Compact is a comprehensive system of health care that serves all 228 federally recognized tribes in Alaska. IHS-funded, tribally-managed hospitals are located in Anchorage, Barrow, Bethe`, `on and Education Assistance Act, Public Law 93-638, as amended. The Alaska Area maintains 11 Title I contracts with Alaska tribes and tribal organizations, and negotiates one Title V compact with 25 s`, `site_content"> Bemidji Area The Bemidji Area Office (BAO) provides service and support to 34 Federally-recognized Tribes and 4 Urban Indian Health programs located in Illinois, Indiana, Michigan, Minnesota and`, `idji Area Office (BAO) provides service and support to 34 Federally-recognized Tribes and 4 Urban Indian Health programs located in Illinois, Indiana, Michigan, Minnesota and Wisconsin. Tribal Health services a`, `, Indiana, Michigan, Minnesota and Wisconsin. Tribal Health services are provided through 11 P.L. 93-638 Title V compacts and 23 Title I contracts. Urban Indian Health programs are located in Chicago, IL; Detroi`, `isconsin. Tribal Health services are provided through 11 P.L. 93-638 Title V compacts and 23 Title I contracts. Urban Indian Health programs are located in Chicago, IL; Detroit, MI; Milwaukee, WI; and`, `porations. Native Americans for Community Action, Inc. (NACA), founded in 1971, is one of 34 Urban Indian health programs in the United States. NACA provides outpatient, behavioral health, health promotion, and`
- **`system_a`** — `BIA_REGION`, `IHS_AREA`
- **`administrative_region_id_a`** — `CEDAR-ADMREG-100007`, `CEDAR-ADMREG-100012`, `CEDAR-ADMREG-200010`, `CEDAR-ADMREG-100001`, `CEDAR-ADMREG-100008`, `CEDAR-ADMREG-100005`, `CEDAR-ADMREG-100002`, `CEDAR-ADMREG-100011`, `CEDAR-ADMREG-100010`, `CEDAR-ADMREG-100003`, `CEDAR-ADMREG-100004`, `CEDAR-ADMREG-100009`, `CEDAR-ADMREG-100006`, `CEDAR-ADMREG-200001`
- **`region_name_a`** — `Northwest Region`, `Western Region`, `Phoenix Area`, `Alaska Region`, `Pacific Region`, `Midwest Region`, `Eastern Region`, `Southwest Region`, `Southern Plains Region`, `Eastern Oklahoma Region`, `Great Plains Region`, `Rocky Mountain Region`, `Navajo Region`, `Alaska Area`
- **`system_b`** — `HUD_ONAP_AREA`, `IHS_AREA`
- **`administrative_region_id_b`** — `CEDAR-ADMREG-400004`, `CEDAR-ADMREG-400001`, `CEDAR-ADMREG-400007`, `CEDAR-ADMREG-400002`, `CEDAR-ADMREG-400006`, `CEDAR-ADMREG-200010`, `CEDAR-ADMREG-200001`, `CEDAR-ADMREG-400005`
- **`region_name_b`** — `Northern Plains ONAP`, `Alaska ONAP`, `Southwest ONAP`, `Eastern Woodlands ONAP`, `Southern Plains ONAP`, `Phoenix Area`, `Alaska Area`, `Northwest ONAP`
