# Entity freshness — when was each entity last touched by anything

*Generated 2026-09-02 by `code/830_entity_freshness.py` across 139 entity-bearing tables. An update is ANY change: a row appearing, a date advancing, an identifier landing. `built_date` and `fetched_date` are deliberately NOT counted — they say when Cedar ran, not when the entity changed, and 70 tables carry one.*

This answers a question no other instrument can. Coverage says who has a website; cadence says which SOURCE is behind; readiness says which DATASET meets the contract. All three aggregate across entities, so an entity can sit untouched for two years while every one of them reads green.

| | n |
|---|---:|
| entities in the register | 1,555 |
| **appear in NO Cedar row at all** | **0** |
| present but carrying no usable date | 398 |
| last change more than a year ago | 281 |

Median days since last change: **105**. p90: **3,898**. Oldest: **15,715**.

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
| Maserculiq, Inc. | Alaska Native Village Corp | 2004-12-31 | 7,915 | `faads_entity_attribution.csv` |
