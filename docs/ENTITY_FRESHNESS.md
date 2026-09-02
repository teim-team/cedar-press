# Entity freshness — when was each entity last touched by anything

*Generated 2026-09-02 by `code/830_entity_freshness.py` across 153 entity-bearing tables. An update is ANY change: a row appearing, a date advancing, an identifier landing. `built_date` and `fetched_date` are deliberately NOT counted — they say when Cedar ran, not when the entity changed, and 70 tables carry one.*

This answers a question no other instrument can. Coverage says who has a website; cadence says which SOURCE is behind; readiness says which DATASET meets the contract. All three aggregate across entities, so an entity can sit untouched for two years while every one of them reads green.

| | n |
|---|---:|
| entities in the register | 1,555 |
| **appear in NO substantive Cedar row** | **0** |
| (the old, unfixable measure: no row in ANY table, identity layer included) | 0 |
| present but carrying no usable date | 148 |
| last change more than a year ago | 398 |

## Columns REFUSED as build stamps

*A date column that supplies the newest date for 5%+ of the register while holding at most 3 distinct values freshened every one of those entities on the same day. That is what a build does. Refused and named here rather than silently dropped — if one of these is genuinely an entity date, say so and it comes back.*

| table | column | would have won for | distinct values |
|---|---|---:|---|
| `gaming_property_self_published_assertions.csv` | `as_of_date` | 178 | 2026-08-12, 2026-09-02 |
| `anc_ceiling_roster.csv` | `row_disposition_date` | 190 | 2026-09-02 |
| `gaming_property_self_published_claims.csv` | `as_of_date` | 106 | 2026-08-12, 2026-09-02 |
| `gaming_web_harvest_observations.csv` | `as_of_date` | 87 | 2026-09-02 |

Median days since last change: **134**. p90: **1,365**. Oldest: **15,715**.

## The tail — 25 entities nobody has touched longest

| entity | class | last change | days | where |
|---|---|---|---:|---|
| Chefarnrmute, Inc. | Alaska Native Village Corp | 1983-08-24 | 15,715 | `admin_appeal_parties.csv` |
| Gold Creek-Susitna Native Associat | Alaska Native Village Corp | 1984-05-23 | 15,442 | `admin_appeal_parties.csv` |
| Malama Moloka`i Foundation | Native Hawaiian Organizati | 1994-02-25 | 11,877 | `nagpra_notice_entity_bridge.csv` |
| Tetlin Native Corporation | Alaska Native Village Corp | 1996-05-02 | 11,080 | `nagpra_notice_entity_bridge.csv` |
| Piedmont American Indian Associati | State-recognized tribe | 2001-12-31 | 9,011 | `faads_entity_attribution.csv` |
| Cherokee Unlimited, Inc | Individually Native-owned  | 2002-12-31 | 8,646 | `individual_native_firm_contracts.csv` |
| Cherokee - Technical Specialis | Individually Native-owned  | 2003-12-31 | 8,281 | `individual_native_firm_contracts.csv` |
| Many Farms High School | BIE School | 2003-12-31 | 8,281 | `bie_uio_identifier_links.csv` |
| Kugkaktlik, Ltd. | Alaska Native Village Corp | 2004-04-26 | 8,164 | `federal_actions_entity_bridge.csv` |
| Cherokee Integrated Technologi | Individually Native-owned  | 2004-12-31 | 7,915 | `individual_native_firm_contracts.csv` |
| Golovin Native Corporation | Alaska Native Village Corp | 2005-06-07 | 7,757 | `federal_actions_entity_bridge.csv` |
| Cherokee Hardware | Individually Native-owned  | 2005-12-31 | 7,550 | `individual_native_firm_contracts.csv` |
| Cherokee Information Systems Limit | Individually Native-owned  | 2005-12-31 | 7,550 | `individual_native_firm_contracts.csv` |
| Cherokee Midwest Exterminating Com | Individually Native-owned  | 2005-12-31 | 7,550 | `individual_native_firm_contracts.csv` |
| Mary's Igloo Native Corporation | Alaska Native Village Corp | 2006-02-21 | 7,498 | `federal_actions_entity_bridge.csv` |
| Dineega Corporation | Alaska Native Village Corp | 2006-03-08 | 7,483 | `federal_actions_entity_bridge.csv` |
| Hee-Yea-Lingde Corporation | Alaska Native Village Corp | 2006-08-31 | 7,307 | `federal_actions_entity_bridge.csv` |
| Cherokee Products Incorporated | Individually Native-owned  | 2006-12-31 | 7,185 | `individual_native_firm_contracts.csv` |
| Paschal Sherman Indian School | BIE School | 2006-12-31 | 7,185 | `bie_uio_identifier_links.csv` |
| Tulkisarmute, Inc. | Alaska Native Village Corp | 2006-12-31 | 7,185 | `faads_entity_attribution.csv` |
| Lime Village Company | Alaska Native Village Corp | 2007-01-31 | 7,154 | `federal_actions_entity_bridge.csv` |
| Pitka's Point Native Corporation | Alaska Native Village Corp | 2007-06-15 | 7,019 | `federal_actions_entity_bridge.csv` |
| Chickasaw Children's Village | BIE School | 2007-10-01 | 6,911 | `entity_dated_public_facts.csv` |
| Coeur d'Alene Tribal School | BIE School | 2007-10-01 | 6,911 | `entity_dated_public_facts.csv` |
| Shiprock Reservation Dormitory | BIE School | 2007-10-01 | 6,911 | `entity_dated_public_facts.csv` |
