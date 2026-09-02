# Entity freshness — when was each entity last touched by anything

*Generated 2026-09-01 by `code/830_entity_freshness.py` across 137 entity-bearing tables. An update is ANY change: a row appearing, a date advancing, an identifier landing. `built_date` and `fetched_date` are deliberately NOT counted — they say when Cedar ran, not when the entity changed, and 70 tables carry one.*

This answers a question no other instrument can. Coverage says who has a website; cadence says which SOURCE is behind; readiness says which DATASET meets the contract. All three aggregate across entities, so an entity can sit untouched for two years while every one of them reads green.

| | n |
|---|---:|
| entities in the register | 1,555 |
| **appear in NO Cedar row at all** | **0** |
| present but carrying no usable date | 18 |
| last change more than a year ago | 0 |

Median days since last change: **25**. p90: **25**. Oldest: **98**.

## The tail — 25 entities nobody has touched longest

| entity | class | last change | days | where |
|---|---|---|---:|---|
| Southcentral Foundation | Federal-level self-governa | 2026-05-26 | 98 | `subawards.csv` |
| Bank Of Cherokee County | Individually Native-owned  | 2026-08-05 | 27 | `individual_native_firm_register.csv` |
| C.I.S. Contracting, Llc | Individually Native-owned  | 2026-08-05 | 27 | `individual_native_firm_register.csv` |
| Cherokee - Technical Specialis | Individually Native-owned  | 2026-08-05 | 27 | `individual_native_firm_register.csv` |
| Cherokee Advanced Systems, Inc | Individually Native-owned  | 2026-08-05 | 27 | `individual_native_firm_register.csv` |
| Cherokee Asphalt Solutions Llc | Individually Native-owned  | 2026-08-05 | 27 | `individual_native_firm_register.csv` |
| Cherokee Chainlink And Constructio | Individually Native-owned  | 2026-08-05 | 27 | `individual_native_firm_register.csv` |
| Cherokee Components, Llc | Individually Native-owned  | 2026-08-05 | 27 | `individual_native_firm_register.csv` |
| Cherokee Construction And Excavati | Individually Native-owned  | 2026-08-05 | 27 | `individual_native_firm_register.csv` |
| Cherokee Construction Enterprises | Individually Native-owned  | 2026-08-05 | 27 | `individual_native_firm_register.csv` |
| Cherokee Construction Inc | Individually Native-owned  | 2026-08-05 | 27 | `individual_native_firm_register.csv` |
| Cherokee Construction Services, Ll | Individually Native-owned  | 2026-08-05 | 27 | `individual_native_firm_register.csv` |
| Cherokee Construction, Inc. | Individually Native-owned  | 2026-08-05 | 27 | `individual_native_firm_register.csv` |
| Cherokee Controls, Inc | Individually Native-owned  | 2026-08-05 | 27 | `individual_native_firm_register.csv` |
| Cherokee Energy Management & Const | Individually Native-owned  | 2026-08-05 | 27 | `individual_native_firm_register.csv` |
| Cherokee Enterprises Inc | Individually Native-owned  | 2026-08-05 | 27 | `individual_native_firm_register.csv` |
| Cherokee Enterprises, Inc. | Individually Native-owned  | 2026-08-05 | 27 | `individual_native_firm_register.csv` |
| Cherokee Fire Protection, Llc | Individually Native-owned  | 2026-08-05 | 27 | `individual_native_firm_register.csv` |
| Cherokee Government Applications L | Individually Native-owned  | 2026-08-05 | 27 | `individual_native_firm_register.csv` |
| Cherokee Hardware | Individually Native-owned  | 2026-08-05 | 27 | `individual_native_firm_register.csv` |
| Cherokee Holdings Llc | Individually Native-owned  | 2026-08-05 | 27 | `individual_native_firm_register.csv` |
| Cherokee Information Services, | Individually Native-owned  | 2026-08-05 | 27 | `individual_native_firm_register.csv` |
| Cherokee Information Systems Limit | Individually Native-owned  | 2026-08-05 | 27 | `individual_native_firm_register.csv` |
| Cherokee Integrated Technologi | Individually Native-owned  | 2026-08-05 | 27 | `individual_native_firm_register.csv` |
| Cherokee Joint Venture Limited Lia | Individually Native-owned  | 2026-08-05 | 27 | `individual_native_firm_register.csv` |
