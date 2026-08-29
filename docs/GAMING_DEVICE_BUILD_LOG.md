# The gaming device layer — build log

*Built 2026-08-07 by `code/117_build_gaming_devices.py`. Every number below is computed by the build and written to `logs/gaming_devices_summary_2026-08-07.json`; none is asserted by hand.*

---

## The honest headline

**A slot-by-slot fleet per property is not buildable from free sources.** No public source anywhere in the United States publishes a dated manufacturer, cabinet, theme and quantity for a named tribal property. What is buildable is *how many devices, of what IGRA class, at what property or tribe, on what date* — and that is what this file holds.

- **1,326 device observations**, 1990-08-02 to 2026-08-06
- **67 of 774 properties (8.7%)** carry at least one device observation
- **97 tribes** carry at least one
- **0 rows name a manufacturer**, 0 name a cabinet, 0 carry a shipment direction

Those three zeros are the measured finding, not an unfinished column. The sweeps behind them are below.

**Read the coverage figure with the right comparison.** The licensed Casino City panel carries dated device counts for **409** properties and, by standing rule, publishes for none of them — it is an internal QA layer and always will be. So the honest statement is not "8.7% is low"; it is that **67 properties can be device-counted from sources a subscriber can audit**, and that the remainder is a publishing constraint imposed by what regulators publish, not by what Cedar has looked for. Every state in the 18-state priority sweep is closed with a documented answer in `docs/GAMING_CAPACITY_OFFICIAL_LOG.md`.

## Observations by type

| observation_type | n |
|---|---:|
| `REGULATORY_INVENTORY` | 1,072 |
| `AUTHORIZED_MAXIMUM` | 241 |
| `FLOOR_COUNT` | 13 |

## Observations by source

| prefix | n | source |
|---|---:|---|
| `GDO-CAP-` | 989 | state regulators + SEC-filed issuer counts, re-projected from `gaming_capacity_official.csv` |
| `GDO-WI-` | 168 | Wisconsin Legislative Fiscal Bureau per-casino slot counts, seven biennial editions, via `state_gaming_observations.csv` |
| `GDO-WAA-` | 75 | Washington per-tribe player-terminal allocations, via `wa_machine_allocations.csv` |
| `GDO-CST-` | 63 | compact device caps written into the instrument, via `compact_structured_terms.csv` |
| `GDO-OK-` | 24 | Oklahoma OMES Gaming Compliance Report, statewide monthly average Class III machines (NEW EXTRACTION, 12 editions) |
| `GDO-AZR-` | 7 | Arizona ADG FY2025 Annual Report (NEW EXTRACTION) |

**Never sum this file with `gaming_capacity_official.csv`.** Most rows re-express the same facts in a device-shaped schema with a typed `device_class`; the `source_url` and `source_quote` are the original publisher's in both files.

## Class II / Class III is a DATED OBSERVATION

> Elijah, 2026-08-07: *"at any time a tribe can change their status by swapping out their machines, so it's a necessary but not sufficient condition."*

A floor can be converted between classes with no federal record. So `device_class` sits on the observation with its own date and source, and **there is no device-class column on any property anywhere in Cedar**. Blank means *the source did not say*, never *unknown class*.

| device_class | n |
|---|---:|
| (unstated by source) | 996 |
| Class III | 163 |
| Class III (Tribal Lottery System player terminal) | 130 |
| Class III (DCETG) | 26 |
| Class II | 11 |

Arizona is the only regulator in the country that publishes the split per casino, in separate Class III and Class II columns of the *Status of Tribal Gaming in Arizona* report, and it does so only for the editions Cedar has recovered.

## An authorised maximum is never an operating count

`cedar_domain.may_promote()` is imported and asserted at module import **and again per row**; a build that ever produced an `AUTHORIZED_MAXIMUM` presented as a floor count would fail loudly rather than publish.

Washington's **1,075 player terminals per tribe** is an entitlement, and **six of the twenty-nine holders operate no casino at all** — Hoh, Lower Elwha, Makah, Quileute, Samish, Sauk-Suiattle. Statewide authorised total 29 × 1,075 = **31,175**.

## Arizona runs the same market, and its ledger is NOT public

The brief asked directly. The answer is documented, from ADG's own annual report:

> "Currently, 16 Arizona Tribes operate 26 Class III casinos in the State. Another six Tribes do not have casinos but have slot machine rights that they may lease to other Tribes with casinos (transfer agreements)."
> — Arizona Department of Gaming, FY2025 Annual Report

The six are named on the same page under *Compacted Tribes without Casinos*: **Havasupai · Hopi · Hualapai · Kaibab Band of Paiute · San Juan Southern Paiute · Zuni**. Each is emitted as an `AUTHORIZED_MAXIMUM` row with a **blank quantity**, because ADG states that the right exists and is leasable and states no number.

ADG holds the transfer agreements — its own audit page lists *Transfer Agreements* among the things the Compact Compliance team reviews — but **publishes no ledger**. `gaming.az.gov/resources/reports` was enumerated this build: 36 linked PDFs, and not one is an allocation or transfer table. So **Arizona's transferable-rights ledger needs a public-records request, exactly like Washington's**, and for the same structural reason: the regulator receives the instrument and publishes a workload count.

**Washington was not re-attempted**, per the brief and per `docs/WA_ALLOCATION_BUILD_LOG.md`: since Appendix X2 (2007) WSGC receives only *the number of transfers*, not the transfer documents, and the price sits by design in a separate agreement that is never filed.

## Does any state publish shipment-level detail?

**No.** The places a dated manufacturer + model + quantity would have to surface were swept and measured:

- NIGC declination corpus swept: 158 OCR'd letters, 4 mention a gaming machine at all, 0 name a device manufacturer. No letter carries a manufacturer + model + quantity for a named property, so no MANUFACTURER_PLACEMENT row is derivable from the federal declination record.
- Tribal gaming issuer filings swept: 38 Mohegan / Seneca 10-K and S-4 documents, 2 mention a slot manufacturer at all and 0 mention one in a supply, lease or purchase context. The only mentions are an officer's prior employer in a biography ("positions of increasing responsibility at Scientific Games Corporation"). A tribal issuer reports how many machines it operates and never who built them.

Manufacturer newsrooms were probed directly rather than assumed: `playags.com/news` and `lnw.com/newsroom` both answer HTTP 308 to a plain GET and `everi.com/news` returns a JavaScript index whose headlines carry no property install. A manufacturer press release naming a specific property and a device count is the one property-level placement source that exists in principle; it is irregular, marketing-driven and was not obtained here. **Zero fabricated placements were written to fill the column.**

Add to that the state sweep already closed in `docs/GAMING_CAPACITY_OFFICIAL_LOG.md`, where all 18 priority states carry a documented answer. **Machine shipment and transport records exist** — a Washington tribe cannot switch on an acquired terminal without filing, and Arizona certifies every machine before it runs — **but what reaches the public is a count of regulatory actions, never the movement.**

## Extraction findings, recorded rather than smoothed

- Oklahoma FY2017: OMES reports [41382, 41395] for the same fiscal year across editions GameCompAnnReport2017.pdf, GameCompAnnReport2018.pdf - both kept, neither adjusted.
- Arizona: the FY2025 ADG annual report's Machine Compliance panel carries what looks like a device-flow number - the linear text layer renders it as 'Total Games Approved 8,007 537 1,478 Promotions/Lotteries 144 Poker Tournaments Machines Casino 244 Other Approved Submissions 34 New/Revised Table Games Certified Visits'. Two infographic columns are INTERLEAVED with a third, so which number belongs to 'Machines Certified' can only be settled by reading word coordinates, not the text layer. WITHHELD. This is the same failure mode as the Michigan payment tables and the Arizona status report, and the same answer: read positions and foot the result, or do not publish the number.

- **Oklahoma's series is deliberately double-stated.** Each OMES edition reports its own fiscal year AND the prior one, so most years appear twice from two independent editions. Both rows are kept: two editions agreeing is corroboration, and the one year where they **disagree** — FY2017, 41,395 against 41,382 — is the finding above. Deduplicating to one row per year would have hidden it.
- **Oklahoma changed its own statistic mid-series.** Through the FY2014 edition OMES reported a LEVEL (*"there were 39,936 Class III machines"*); from FY2015 it reports a MONTHLY AVERAGE (*"a monthly average of 40,667"*). Two different quantities under one heading, so the basis travels in `confidence` on every Oklahoma row rather than the two being pooled into one series.

## Manufacturer facts — company-level, never a property

`data/clean/gaming_manufacturer_facts.csv`, **62 facts** from 4 issuers.

- **Everi Holdings Inc.** — 9 facts, FY2022–FY2024
- **International Game Technology PLC** — 6 facts, FY2021–FY2023
- **Light & Wonder, Inc.** — 10 facts, FY2021–FY2025
- **PlayAGS, Inc.** — 37 facts, FY2020–FY2024

**The rule on every row:** a manufacturer's installed base, participation units or units sold measures *the manufacturer's* economics. It is never converted into a casino's gaming revenue and never apportioned to a property. `property_attributed` says so on every row, in words, so a downstream reader cannot miss it.

**Every KPI row is accepted only if the filing's own variance column foots** (n1 − n2 == variance) **and its fiscal year is bound from the table's own header year pair**, never from the filing date. A candidate failing either test is refused to `data/raw/external/gaming_devices/manufacturer_kpi_refused_2026-08-07.csv` — currently 0, so that file is not written. That is the same discipline that caught the one-row column shift in the Michigan payment tables and the Arizona status report: **read the document's own check, or do not publish the table.**

Three extraction defects were found and fixed during this build, each of which would have shipped a plausible wrong number or a plausible wrong absence:

1. **A two-year regex reverses the columns.** Over `December 31, 2024 December 31, 2023 2024 vs 2023` a `(20\d\d)\D{1,80}?(20\d\d)` match consumes the wrong overlap and returns **(2023, 2024)**. Six correct Everi rows were refused on the first pass. Fixed by collecting every year and walking adjacent pairs backwards from the label.
2. **A one-sided context window lost the class split.** AGS prints `EGM installed base: Class II` in FY2022–FY2024 but `EGM unit information: Class II` in FY2020–FY2021, reaching the words *installed base* only on the following line. A backward-only window silently dropped two years of the only per-class series in the file.
3. **A three-digit minimum on the variance column dropped a real row.** AGS FY2022 prints `Class II 11,251 11,256 (5 ) (0.0 )%`; requiring three digits in the variance refused it while every neighbouring row published.

And one **containment false positive inside a sweep whose entire purpose was to measure an absence**: without word boundaries, `Everi` matches inside *sev-**eri**-ty* and reported **42 phantom manufacturer mentions** across the tribal issuer filings. Unbounded, the sweep would have published the opposite of the truth — that issuers DO name their suppliers. Bounded, the real count is two, both a CFO's prior employer.

### Two things the filings say that nothing else in the market carries

- **PlayAGS splits its installed base by IGRA class.** Its FY2024 10-K prints `EGM installed base: Class II 10,685 / Class III 5,875` — the only Class II device count of national scope available for free anywhere, and it is the *manufacturer's* base, not any tribe's floor.
- **Light & Wonder names where Class II lives.** *"These Class II and centrally determined systems primarily operate in Native American casinos in Washington, Florida, Alabama and Oklahoma."*

### The hole that will not close from free sources

**Konami Gaming Inc.** is a major supplier to Indian Country and its parent **delisted from the NYSE in 2015**. It files nothing current with the SEC, so there is no free filing-based installed base for it. **Aristocrat** is ASX-listed and files nothing with the SEC either. Both are named as principal competitors inside the filings this build does hold — *"Aristocrat and Everi are our primary competitors in the Class II market"* — which is how we know the gap is a gap and not an absence.

**Inspired Entertainment** was pulled (four 10-Ks) and yielded zero device facts: its KPI tables report Virtual Sports and Interactive venues, not an EGM installed base. Retrieved, read, and returned nothing — recorded so the next pass does not re-pull it.

Also dated: **International Game Technology PLC now files as Brightstar Lottery PLC and reports IGT Gaming as *discontinued operations***, so its newest 20-F carries no gaming installed base at all. A newest-edition-wins rule would have returned an empty IGT and looked like a retrieval failure.

## What is structurally unobtainable

1. **A per-property fleet.** Which cabinets, from which manufacturer, running which themes, are on a given floor is commercial information held by the tribe, its gaming commission and its vendors. No statute makes it public.
2. **Shipment records.** The Johnson Act (15 U.S.C. § 1173) registration and reporting regime runs to the Attorney General, not to a public docket. State device-transport notifications go to the state gaming agency and are not published.
3. **The moment a floor changes class.** A Class II floor can be swapped to Class III with no federal filing, which is precisely why class is stored dated and never as an attribute.
4. **Executed inter-tribal rights transfers, in both markets that have one.** Washington by documented narrowing (2007), Arizona by the regulator simply not publishing. Both need a public-records request.
5. **Konami and Aristocrat unit counts**, per above.

## Review queue

`review/gaming_device_unresolved_2026-08-07.csv` — **22 rows**, blank `YOUR_RULING`, project reconcile-queue format. The dominant reason is a regulator's casino name that does not exactly match a Cedar property name; those rows are kept at tier B with their tribe, never snapped to a nearest match.

## Rules honoured

- **Zero fabrication** — every row carries `source_url` and a verbatim `source_quote`; rows missing either are refused to the queue rather than trusted. The Arizona hard-coded quotes are re-verified against the PDF's text layer at build time and the rows are withheld if a quote has drifted.
- **No second name matcher** — `resolve_entity` is imported from `code/33_apply_party_rulings.py`. What was added is a **refusal**, not a matcher: an Arizona rights holder must resolve to a *federally recognised* class AND be an Arizona tribe. That is what makes the spine's short name *San Juan* resolving to San Juan Southern Paiute of Arizona correct rather than lucky. The Arizona test reads Cedar's own `compacts.csv` rather than a hard-coded state, because **the Zuni Tribe of the Zuni Reservation is seated in New Mexico and holds three Arizona compacts** — a bare state check would have refused a correct resolution.
- **Aliases, not new properties** — the build asserts that every `facility_id` written already exists in `gaming_facilities.csv`.
- **`may_promote` asserted at import and per row.**
- **No modelled property revenue anywhere.**
- **Codebook written as a fragment** under `data/clean/codebook/`; `codebook_master.csv` was not touched.
- **Not edited:** `gaming_capacity_official.csv`, `wa_machine_allocations.csv`, `compact_structured_terms.csv`, `gaming_facilities.csv`, `gaming_property_capacity_history.csv`, `nigc_*`, `ca_gaming_*`, `fl_*`, `tribal_tax_bases.csv`, `prime_contracts.csv`, `federal_funding_transactions.csv`, `subawards.csv`, `entity_*`, the identifier ledger, the spine.

## Files

```
code/117_build_gaming_devices.py
data/clean/gaming_device_observations.csv     1,326 rows
data/clean/gaming_manufacturer_facts.csv      62 rows
data/clean/codebook/07h_gaming_device_observations.csv
data/clean/codebook/07i_gaming_manufacturer_facts.csv
data/raw/external/gaming_devices/             _SOURCE_MANIFEST.csv + md5s
review/gaming_device_unresolved_2026-08-07.csv   22 rows
logs/gaming_devices_summary_2026-08-07.json
docs/GAMING_DEVICE_BUILD_LOG.md
```
