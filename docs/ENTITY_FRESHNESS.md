# Entity freshness — when was each entity last touched by anything

*Generated 2026-09-02 by `code/830_entity_freshness.py` across 145 entity-bearing tables. An update is ANY change: a row appearing, a date advancing, an identifier landing. `built_date` and `fetched_date` are deliberately NOT counted — they say when Cedar ran, not when the entity changed, and 70 tables carry one.*

This answers a question no other instrument can. Coverage says who has a website; cadence says which SOURCE is behind; readiness says which DATASET meets the contract. All three aggregate across entities, so an entity can sit untouched for two years while every one of them reads green.

| | n |
|---|---:|
| entities in the register | 1,555 |
| **appear in NO substantive Cedar row** | **83** |
| (the old, unfixable measure: no row in ANY table, identity layer included) | 0 |
| present but carrying no usable date | 290 |
| last change more than a year ago | 287 |

## Columns REFUSED as build stamps

*A date column that supplies the newest date for 5%+ of the register while holding at most 3 distinct values freshened every one of those entities on the same day. That is what a build does. Refused and named here rather than silently dropped — if one of these is genuinely an entity date, say so and it comes back.*

| table | column | would have won for | distinct values |
|---|---|---:|---|
| `gaming_web_harvest_observations.csv` | `as_of_date` | 191 | 2026-09-02 |

Median days since last change: **112**. p90: **3,627**. Oldest: **15,715**.

## The tail — 25 entities nobody has touched longest

| entity | class | last change | days | where |
|---|---|---|---:|---|
| Chefarnrmute, Inc. | Alaska Native Village Corp | 1983-08-24 | 15,715 | `admin_appeal_parties.csv` |
| Tanalian, Inc. | ANCSA Group Corporation | 1983-08-30 | 15,709 | `admin_appeal_parties.csv` |
| Gold Creek-Susitna Native Associat | Alaska Native Village Corp | 1984-05-23 | 15,442 | `admin_appeal_parties.csv` |
| Malama Moloka`i Foundation | Native Hawaiian Organizati | 1994-02-25 | 11,877 | `nagpra_notice_entity_bridge.csv` |
| Tetlin Native Corporation | Alaska Native Village Corp | 1996-05-02 | 11,080 | `nagpra_notice_entity_bridge.csv` |
| Na Koa Ikaika Ka Lahui Hawaii | Native Hawaiian Organizati | 1997-08-27 | 10,598 | `nagpra_notice_entity_bridge.csv` |
| Order of Kamehameha I | Native Hawaiian Organizati | 1998-01-28 | 10,444 | `nagpra_notice_entity_bridge.csv` |
| Bristol Bay Housing Authority | Intertribal Organization | 1998-04-03 | 10,379 | `section_106_consultation_events.csv` |
| Duckwater Shoshone Elementary Scho | BIE School | 2000-05-08 | 9,613 | `nagpra_notice_entity_bridge.csv` |
| Mariano Lake Community School | BIE School | 2000-05-25 | 9,596 | `admin_appeal_parties.csv` |
| Cherokee Construction, Inc. | Individually Native-owned  | 2000-12-31 | 9,376 | `individual_native_firm_contracts.csv` |
| Aha Kukaniloko Koa Mana mea ola ka | Native Hawaiian Organizati | 2001-11-13 | 9,059 | `nagpra_notice_entity_bridge.csv` |
| Aneth Community School | BIE School | 2001-12-31 | 9,011 | `bie_uio_identifier_links.csv` |
| Dennehotso Boarding School | BIE School | 2001-12-31 | 9,011 | `bie_uio_identifier_links.csv` |
| Piedmont American Indian Associati | State-recognized tribe | 2001-12-31 | 9,011 | `faads_entity_attribution.csv` |
| Sanostee Day School | BIE School | 2001-12-31 | 9,011 | `bie_uio_identifier_links.csv` |
| Wingate High School | BIE School | 2001-12-31 | 9,011 | `bie_uio_identifier_links.csv` |
| Cherokee Unlimited, Inc | Individually Native-owned  | 2002-12-31 | 8,646 | `individual_native_firm_contracts.csv` |
| Cherokee - Technical Specialis | Individually Native-owned  | 2003-12-31 | 8,281 | `individual_native_firm_contracts.csv` |
| Clifton Choctaw Tribe of Louisiana | State-recognized tribe | 2003-12-31 | 8,281 | `faads_entity_attribution.csv` |
| Many Farms High School | BIE School | 2003-12-31 | 8,281 | `bie_uio_identifier_links.csv` |
| Kugkaktlik, Ltd. | Alaska Native Village Corp | 2004-04-26 | 8,164 | `federal_actions_entity_bridge.csv` |
| Hui Mālama Ola Nā ‘Ōiwi | Native Hawaiian Organizati | 2004-10-12 | 7,995 | `nagpra_notice_entity_bridge.csv` |
| Cherokee Integrated Technologi | Individually Native-owned  | 2004-12-31 | 7,915 | `individual_native_firm_contracts.csv` |
| Occaneechi Band of the Saponi Nati | State-recognized tribe | 2004-12-31 | 7,915 | `faads_entity_attribution.csv` |

## Present in the register, absent from every dataset — 83

These are the entities the owner has been asking about since August: they exist in the identity layer and no Cedar dataset has a single row for them.

*Measured OUTSIDE the identity layer — see `IDENTITY_LAYER` in this script. Counting those files, one of which is this script's own output, pinned this number at zero and it had been reading zero ever since. `code/1021_register_only_first_rows.py` works this list.*

| entity | class |
|---|---|
| Ahfachkee School | BIE School |
| Atsá Biyáázh Community School | BIE School |
| Baca /Dlo'Ay Azhi Community School | BIE School |
| Beclabito Day School | BIE School |
| Blackfeet Dormitory | BIE School |
| Bogue Chitto Elementary | BIE School |
| Bread Springs Day School | BIE School |
| Cherokee Central Elementary School | BIE School |
| Cherokee Central High School | BIE School |
| Cherokee Central Middle School | BIE School |
| Cheyenne-Eagle Butte High School | BIE School |
| Chi Chil'tah Community School | BIE School |
| Chickasaw Children's Village | BIE School |
| Chitimacha Tribal School | BIE School |
| Choctaw Central High School | BIE School |
| Choctaw Central Middle School | BIE School |
| Circle of Life Academy | BIE School |
| Coeur d'Alene Tribal School | BIE School |
| Conehatta Elemenatary School | BIE School |
| Cottonwood Day School | BIE School |
| Cove Day School | BIE School |
| Crow Creek Reservation High School | BIE School |
| Crow Creek Tribal Elementary School | BIE School |
| Crystal Boarding School | BIE School |
| Dunseith Indian Day School | BIE School |
| Eufaula Dormitory | BIE School |
| Flandreau Indian School | BIE School |
| Fond du Lac Ojibwe School | BIE School |
| Greyhills Academy High School | BIE School |
| Havasupai Elementary School | BIE School |
