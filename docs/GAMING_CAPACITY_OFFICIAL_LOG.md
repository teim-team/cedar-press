# Gaming capacity — the authoritative-source layer

*Started 2026-08-06, continued and closed 2026-08-07. Scripts:
`code/91_extract_compact_authorizations.py`,
`code/92_build_gaming_capacity_official.py`,
`code/93_extract_az_gaming_status.py`,
`code/94_extract_mi_mgcb_revshare.py` (new),
`code/95_wayback_az_gaming_status.py` (new),
`code/96_extract_sec_property_capacity.py` (new),
`code/97_extract_az_status_archive.py` (new).*

*Output: `data/clean/gaming_capacity_official.csv`. Queues:
`review/gaming_capacity_official_unresolved_2026-08-07.csv`,
`review/gaming_capacity_vendor_vs_official_2026-08-07.csv`,
`review/gaming_capacity_vendor_vs_official_distribution_2026-08-07.csv`.*

Companion to `docs/GAMING_SPEC_RECONCILIATION.md` (the backbone ruling) and
`docs/GAMING_TEMPORAL_BUILD_LOG.md` (the vendor layer this one replaces the
*source* of).

---

## Why this exists

`data/clean/gaming_property_capacity_history.csv` holds **64,181 dated
observations across 10 metrics for 409 properties, 2001–2023**. Every single one
carries the same two values:

```
source      = "Casino City Press gaming-property panel (tribal_casino_panel.dta)"
value_basis = reported
```

One vendor. Zero independent observations. That is two problems, not one.

**Evidentiary.** The vendor does not disclose how it counts. Elijah, 2026-08-06:
*"casino city isnt really clear where they get stuff and they say they have
relationships or go out to properties but if we have more authoritative sources
thats valuable."* A subscriber cannot audit a single number in that file.

**Commercial.** Elijah, same day: *"im basically saying we cant just resell
casinocity lol, but it could be a source of internal fact checking if that makes
sense."* This is the DUNS rule one level up — join on it internally, never
republish it. `code/87_build_dataset_notes.py` enforces it: both vendor files sit
in `LICENSED_SOURCE_FILES`, get no notes contract, and therefore cannot ship by
accident.

So the vendor layer stays, unchanged, as an internal fact-checking layer. This
build produces the layer that **ships**.

---

## What is in the file now

**6,461 observations** (from 6,027 at the previous checkpoint), none from the
vendor, every row carrying a `source_url` and a verbatim `source_quote` —
verified mechanically: **0 of 6,461 rows missing either**.

| measurement_status | n | measurement_type | what it means |
|---|---:|---|---|
| `reported_revenue` | 2,566 | `REGULATORY_REPORTED_COUNT` | a regulator publishes actual revenue |
| `reported_payment` | 1,503 | `REGULATORY_REPORTED_COUNT` | a tribe's payment, as the payee reports it |
| `reported_measurement` | 1,160 | `REGULATORY_REPORTED_COUNT` | a count of things that exist |
| `authorization` | 692 | `AUTHORIZED_MAXIMUM` | a **ceiling**. What a tribe MAY operate |
| `proposed` | 364 | `PROJECTED` | a facility described in an environmental review |
| `audited_filing_measurement` | 148 | `PROPERTY_REPORTED_COUNT` | an SEC 10-K count, signed under §302 |
| `exact_derived_revenue` | 28 | `COMPACT_REPORTED_COUNT` | `payment / statutory rate`, exact arithmetic |

**These seven are never pooled.** Every metric that is a ceiling ends in
`_authorized_max`, so the distinction survives any downstream filter, join or
chart.

New this pass: the file now carries a **`measurement_type` column** typed from
`cedar_domain.MeasurementType`, and the build **asserts `may_promote` at import**
for `AUTHORIZED_MAXIMUM`, `PROJECTED` and `ENVIRONMENTAL_REVIEW_COUNT` against
`ACTIVE_FLOOR_COUNT`. A future edit to `cedar_domain` that weakened the promotion
guard now fails this build loudly instead of quietly letting a compact device cap
publish as a device count.

### Observations by state and evidence layer

| state | AG regulator | BD audited filing | CP compact | CT open data | NEPA | **total** |
|---|---:|---:|---:|---:|---:|---:|
| CT | | 112 | | 2,988 | | **3,100** |
| NM | 1,072 | | 18 | | | **1,090** |
| OK | 624 | | | | 56 | **680** |
| AZ | 411 | | 52 | | | **463** |
| CA | | | 177 | | 173 | **350** |
| WA | 5 | | 208 | | 59 | **272** |
| MI | 160 | | 14 | | 26 | **200** |
| OR | | | 83 | | 1 | **84** |
| ND | | | 51 | | | **51** |
| NY | | 27 | | | 10 | **37** |
| SD | | | 37 | | | **37** |
| WI | | | 12 | | 12 | **24** |
| MA | | | 1 | | 19 | **20** |
| NV | | | 16 | | | **16** |
| MT | 6 | | | | 8 | **14** |
| PA | | 9 | | | | **9** |
| NC | | | 8 | | | **8** |
| WY | | | 4 | | | **4** |
| FL | | | 2 | | | **2** |
| **all** | **2,278** | **148** | **683** | **2,988** | **364** | **6,461** |

**110 of 774 properties** carry at least one non-vendor observation and **239
tribes** do. Of those 110 properties, **54 also appear in the vendor panel, so 56
properties hold coverage the vendor never had** — and 378 vendor-panel properties
remain vendor-only.

---

## What this pass added, and the defect behind each

### 1. Michigan — 145 rows, and a one-row column shift that would have moved money onto the wrong nations

`code/94_extract_mi_mgcb_revshare.py`. Michigan went from **15 observations to
200**.

MGCB publishes two per-tribe payment tables nothing else in the market carries at
tribe granularity: **Tribal 2% Payments to Local Units of State Government** and
**Tribal Payments to the Michigan Strategic Fund / MEDC**, both 1993 → current.
The previous pass reached 15 rows. The reason is the finding:

> **`pdftotext -layout` shifts the tribe-name column by one row.**

MGCB sets the tribe name and its numbers on baselines 1–2 points apart, so the
linear text layer emits tribe *N*'s money on the line carrying tribe *N+1*'s
name. Read linearly, Bay Mills' money lands on Grand Traverse, Grand Traverse's
on Gun Lake, and so on down the whole column — **every row well-sourced, every
row attached to the wrong nation.** It is AGENTS.md's containment defect in a
different costume, and the *same* shift is present in the MGCB Annual Report's
text layer, so a second reader would have confirmed the first reader's error.

The extractor reads **word positions**, groups baselines within a tolerance,
assigns each number to a column by its **right edge** (right edges are stable
across digit counts; left edges are not) against bands learned from the printed
TOTALS row, then **foots every column against that TOTALS row**. All **18
columns across both PDFs foot exactly**:

```
local  cumulative 497,283,223.17 = 497,283,223.17   ... 2025 30,614,994.91 = 30,614,994.91
MSF    cumulative 814,777,637.83 = 814,777,637.83   ... 2025 15,436,190.49 = 15,436,190.49
```

A second, independent check confirms the assignment per row rather than per
column: Bay Mills' cumulative 1993–2017 total plus its seven year columns equals
its printed life-to-date total **to the cent** (12,313,271.56 + 2,504,427.69 =
14,817,699.25). The linear reading fails that identity for every row.

Two payees, **two metric names**. `payment_to_local_government` and
`payment_to_state` are separate metrics on purpose — one name for both would
silently stack two unrelated obligations into a single series.

Only the seven explicit year columns publish. `cumulative_prior` spans an
unstated multi-year window and `ltd_total` is a life-to-date cumulative; both are
extracted, footed and then withheld, because a cumulative published beside annual
figures is a double count waiting to happen.

### 2. Michigan again — 28 rows of **exact derived revenue**, spec 9.4's one honest route

Spec 9.4: *"Where a public payment meets an invertible formula, `payment / rate`
is exact arithmetic — the one honest route to real property revenue — provided
the revenue concept is preserved."* Michigan is the case.

The 1999 Michigan compacts state the formula verbatim, and the clause was
verified **word for word in all four** of the 1999 compact texts this project
already holds:

> *"Payment in the aggregate amount equal to two percent (2%) of the net win at
> each casino derived from all Class III electronic games of chance, as those
> games are defined in this Compact."*

So **net win from Class III electronic games = 2% payment / 0.02, exactly**. 28
tribe-years for Little River, Little Traverse Bay Bands, Nottawaseppi Huron and
Pokagon, 2019–2025. Michigan otherwise publishes **no** tribal gaming revenue at
all.

Three limits ride on every derived row rather than waiting to be discovered:

1. **The revenue concept is narrow.** Net win from **Class III electronic games
   of chance only** — no table games, no Class II, no poker, no non-gaming.
   Calling it "casino revenue" would understate a great deal, which is the
   subtler and more dangerous error.
2. **It is tribe-level.** The clause says *"the aggregate amount … at each
   casino"*, so a tribe with three casinos remits one number covering all three.
   `facility_id` stays blank and that blank is meaningful.
3. **It covers four tribes, not twelve.** The 1993 compact texts on disk contain
   **no 2% clause** — that obligation arrives through Consent Judgments this
   project does not hold. MGCB's annual report prints "2%" against every tribe,
   but *a regulator's summary table is not the operative instrument*, and a
   derivation is only as good as its instrument. The other eight tribes publish
   as payments only.

Footnoted tribe-years are excluded **by flag, not silently**: MGCB's own
footnotes say some totals include escrow, excess distributions or a prorated
advance, and for those years `payment / 0.02` is not the net win.

### 3. SEC filings — 148 audited per-property counts, the layer specified in 2026-08-06 and never populated

`code/96_extract_sec_property_capacity.py`. Script 92 declared a bond/SEC layer
and `agent_bond_sec_2026-08-06.csv` was never written, because the agent assigned
to it died. **The documents survived on disk**:

```
data/raw/external/gaming_official/sec_filings/txt/
  27 Mohegan Tribal Gaming Authority 10-Ks   FY1996 - FY2022
  11 Seneca Gaming Corporation 10-K / S-4    FY2004 - FY2009
```

This is the strongest evidence class in the build. A 10-K is signed under
§302 by named officers; a regulator's roster is not. It is also the **only**
per-property, per-year device series for Mohegan Sun, because the vendor panel
holds zero Connecticut rows and the Connecticut regulator publishes a weighted
monthly average rather than a count.

**A gaming 10-K describes three kinds of casino floor and they read
identically.** Mohegan's FY2005 filing contains, within a few hundred characters
of each other: *"approximately 3,800 slot machines"* (its own), *"Turning Stone
Casino Resort currently has approximately 2,100 VLTs … and 350 hotel rooms"* (the
Oneida Nation's — a competitor), and *"projected to have 220 hotel rooms"*
(Seneca's then-unbuilt Salamanca facility). Matching numbers near the phrase
"slot machines" pulls all three and attributes all three to Mohegan.

Five guards, each of which caught something real. **1,168 windows were refused
and every refusal is written to `agent_bond_sec_rejected_2026-08-07.csv` with its
reason**, so the refusals are auditable rather than invisible:

| n refused | guard |
|---:|---|
| 215 | window names an **area** of the property, not the property (below) |
| 194 | **forward-looking** language — `may_promote` refuses PROJECTED → ACTIVE |
| ~330 | window names a **competitor** property |
| ~290 | 0 or ≥2 issuer properties named — a bullet fragment is never assigned to the nearest heading |
| 49 | the same filing states two values for one property-metric-date |
| — | window describes a **statutory ceiling** (below) |

**The area guard is the one worth transferring.** Mohegan's 10-K never states a
single Mohegan Sun device count. It states three, one per named casino inside the
one property:

> *"Mohegan Sun currently operates in an approximately 3.1 million square-foot
> facility, which includes the following: **Casino of the Earth** — As of
> September 30, 2015, Casino of the Earth offered … approximately 2,605 slot
> machines and 135 table games …"*

Casino of the Earth / of the Sky / of the Wind are **areas of one property, not
three properties**, and the filing dates each explicitly. Each is emitted with
`applies_to = area_of_property:<area>`; the property total is emitted **only
where all three areas are present in the same filing** — the same rule script 92
applies to Arizona's Class III + Class II derivation, because a total built from
two of three areas publishes a partial floor as a whole one. Both the area rows
and the derived total carry `exclusion_flag`, so one filter separates them from
figures the filing states directly.

Without that guard, pass 1 published **Casino of the Earth's FY2011 3,400 devices
as Mohegan Sun's whole floor** while pass 2 was correctly deriving 6,325 for the
same date — the file would have contradicted itself.

The resulting Mohegan Sun series, all from areas that foot to a stated whole:

```
FY2010 6,425   FY2013 5,530   FY2016 5,045
FY2011 6,325   FY2014 5,390   FY2017 4,900
FY2012 5,815   FY2015 5,140   FY2018 4,485
```

**The ceiling guard** was added after the plausibility gate caught
`gaming_machines = 61,000` on Mohegan Sun Pocono. The source: *"An aggregate of
61,000 slot machines may be permitted for up to 14 locations throughout
Pennsylvania"* — the 2004 Pennsylvania statewide licence pool. It is now refused
at extraction. **The guard's first version was too wide and was measured as
such**: rejecting on `legislation`, `licensees`, `statewide` and `limited to`
also killed two genuine Seneca Allegany device counts, because those words appear
in the ordinary legal prose around a real number. Narrowed to phrases that
qualify *the number itself*, both Seneca counts returned and the 61,000 stayed
out. That is the same discipline script 91 had to learn when its tribe-token
guard rejected 1,359 correct sentences.

### 4. An entity-class refusal — the Chickasaw Children's Village defect, caught live

`resolve_entity` is the one resolver and no second matcher was written. But the
Michigan ingest produced this:

```
"Keweenaw Bay Indian Community"        -> TCU-KWNWB1-00  Keweenaw Bay Ojibwa Community College
"Confederated Salish & Kootenai Tribes" -> TCU-...        Salish Kootenai College
```

Ten Michigan payment observations were attributed to a **tribal college**. The
spine holds the correct entity two rows away (`TRBF-KWNWBY-00 Keweenaw`,
Federally recognized tribe, MI). This is AGENTS.md's `Chickasaw Nation →
Chickasaw Children's Village` defect — the one that moved $2.8B onto a school —
reproduced exactly, by the resolver's containment tier.

The fix is a **refusal, not a matcher**. A gaming regulator's device count,
casino payment or compact ceiling is never about a college, a school, a clinic or
a lender, so resolutions to `Tribal College or University`, `BIE School`,
`Urban Indian Organization` and the two financial-institution classes are
rejected and queued for a ruling. A guard that refuses is not a matcher that
guesses.

Four compact authorisations with **neither a tribe nor a state** — a device cap
and two wager limits reading `Tribal-State Gaming Compact,  (approved by the
Secretary of the Interior)` — also shipped in the 2026-08-06 build and are now
queued. A well-formed row about nobody is worse than a queue item, because it
looks publishable.

### 5. Arizona back-catalogue — the snapshot became a panel

`code/95_wayback_az_gaming_status.py` drained the item script 92 queued on the
`web.archive.org` host lock on 2026-08-06 and never ran. The lock's holder
(script 89, PID 30908) was dead and its claim was >6h old, so the lock was taken
over under PULL_DISCIPLINE rule 2 and rewritten in this script's name before the
first request. `code/97_extract_az_status_archive.py` reads what it retrieves.

**Arizona went from 318 observations to 463, and from a 2026 snapshot to dated
editions in 2006, 2012 and 2026.** 145 per-casino rows across two archived
editions: 68 at **2006-02-01** and 72 at **2012-04-01**, covering 21–24 named
casinos each with Class III devices, Class II devices, poker tables and
blackjack tables.

ADG's own page says exactly what the table is:

> *"The Department produces a periodic report which shows the status of Indian
> gaming in Arizona. This report lists the tribes with gaming facilities, their
> location, **how many machines in each facility**, and which casino games are
> available."*
> — `gaming.az.gov/status.htm`, Wayback capture 20070410042237

**The archived editions are a different document from the current one**, which is
why script 93 could not read them: landscape rather than rotated, and with
different columns (Live Keno, Bingo, Off-Track Betting instead of DCETG,
baccarat, craps, roulette). Critically, **they carry no printed TOTALS row**, so
the column-footing check that caught two separate extraction failures in the
current edition is unavailable.

A substitute check was found rather than assumed. The table states
`Current # Sites` per tribe and then lists that tribe's casinos one per row, so
**the document asserts its own row count**. If the positional reader mis-groups
baselines — which is precisely how the linear text layer fails here — the casino
rows recovered for a tribe stop matching the site count that tribe declares.
Every tribe is checked and an edition that does not reconcile is not published.

The check earned its place immediately: the 2012 edition failed on *Fort Mojave
Indian Tribe: declares 1 site, recovered 2 casino rows*. The second row is
`Crossing Casino`, annotated `(closed eff. March 1, 2010)` and showing 0 Class
III devices. ADG's declared site count excludes closed casinos; the table still
lists them. So a casino carrying a trailing `(closed …)` annotation is now
excluded from the reconciliation, **kept as an observation** (a closed
property's last reported floor is still a dated fact), and flagged with the
regulator's own closure note.

And the shift trap is here too. Read linearly, Harrah's Ak-Chin's 1,089 Class III
devices land on Cocopah Casino, Cocopah's 506 on Blue Water, and so on down the
page. Read positionally, Ak-Chin keeps its own 1,089.

**Two columns are deliberately not extracted.** `Bingo` carries bare numbers
(470, 350, 1,500 …) under a header that states no unit — probably seats,
certainly not devices, and publishing them under a guessed metric name would be a
guess wearing a citation. `Live Keno` and `Off-Track Betting` are Yes/No
availability, not counts.

**Seven other retrieved PDFs were refused and named**: the
`TribalContributions*` and `TC_*` files are **ADG press releases carrying a
single statewide quarterly figure** — *"The tribes' combined contributions for
the quarter ended March 31, 2007 was $24,563,568"* — which confirms empirically
what the state table below asserts, that Arizona's tribal contributions are
published in aggregate and never per tribe. They are not per-casino capacity and
they carry no `AS OF` date line, so the extractor rejects them by rule rather
than by filename.

**Still outstanding.** The enumeration found archived editions this run did not
reach, under at least four different filename conventions:

```
Gaming Status Report 020123 / 030123 / 110123 / 060124 / 070124 / 090124 / 020125 / 030125
Status of Tribal Gaming (6-30-22).pdf
currentstatus.pdf · currentstatus7-6-15.pdf · currentstatus10-16-15.pdf · currentstatus11-01-15.pdf
```

`web.archive.org` failed roughly half of all connections with a 21-second connect
timeout throughout the session — a flaky path, **not** a block (the very next
identical request returns 200, and the first CDX call succeeded with 20,000
rows). 14 captures landed. The puller is single-stream, ≥5s gap, exponential
backoff 15→240s, 2h cap, and **checkpoints each prefix's CDX result the moment it
arrives**, because the first run collected all 20,000 rows and then died
mid-retry on a later prefix and lost every one. **Re-running
`code/95_...py` then `code/97_...py` resumes from disk and needs no new
decisions** — the 2015 `currentstatus*` editions sit eight years inside the
vendor window and are the remaining prize.

---

## State-by-state: what each state publishes

Bucket **1** = per-property revenue · **2** = per-tribe or per-property device
counts / payments · **3** = nothing usable below a statewide aggregate.

| State | Bucket | Per-property revenue | Device counts | What is actually published |
|---|:--:|:--:|:--:|---|
| **Connecticut** | **1** | **YES** | **YES** | DCP monthly slot win, handle, contributions **and weighted-average machine count**, per property, 1993–2025, as open data (`data.ct.gov` `i6ts-ib7c`). 748 regulator-months. The single best source in the country. |
| **New Mexico** | **1 (tribe)** | per **tribe**, quarterly | no | NMGCB quarterly Adjusted Net Win **per tribe**, 2002 Q1 – 2022 Q4, 84 reports, 1,072 observations. Plus an official 20-casino roster with addresses. |
| **Arizona** | **2** | no | **YES, per casino, now dated** | ADG *Gaming Status Report* / *Status of Tribal Gaming in Arizona*: 21–26 named casinos × Class III, Class II, table and poker columns + open date + compact date. Live site carries the **current snapshot only**; archived editions recovered from Wayback give **2006-02-01 and 2012-04-01** as well, and more remain (above). Tribal contributions are statutorily **aggregate** (A.R.S. § 5-601.02(H)(1)) — confirmed empirically this pass from ADG's own quarterly press releases, which publish one statewide figure and no tribe split. |
| **Michigan** | **2** | **derived, 4 tribes** | no | MGCB per-tribe 2% local **and** MSF/MEDC payments, 1993–2025, both tables footing exactly. The 1999 compacts state a 2% rate on Class III electronic net win verbatim, making net win exactly derivable for the four 1999-compact tribes. Plus 16 annual reports and a dated 24-casino roster. |
| **Oklahoma** | **2** | no | statewide only | OMES annual report: exclusivity fees **per tribe**, FY2010–FY2025, 624 rows across 11 report editions. Also casinos-per-tribe (138 facilities / 33 tribes) and a statewide monthly average Class III machine count. |
| **Washington** | **2** | no | **authorisations only** | WSGC publishes a 28-casino roster mapped to tribes by the regulator, and the device-**allocation** framework. Per-tribe allocations live in the individual compact PDFs, which this project holds and script 91 mines (208 rows). No operating counts, no per-tribe net receipts. |
| **Montana** | **2** | no | **caps, per tribe** | DOJ Gambling Control Division states a Class III machine cap per tribe in prose (Fort Peck 925, Chippewa Cree 750, Crow 925, Fort Belknap 400, N. Cheyenne 750, CSKT 925). Authorisations, labelled as such. |
| **California** | 2 (weak) | no | **no** | CGCC publishes a 65-casino tribe↔property↔city↔county roster and a 40-tribe SDF/RSTF payer list — good spine material, **zero numeric counts**. RSTF per-tribe money exists but only 2001–2012. **CGCC publishes no gaming device licence counts**; the 1999 licence pool is not published. |
| **New York** | 2 (via SEC) | no | **YES, via 10-K** | The State Gaming Commission publishes nothing per tribal property. Seneca Gaming Corporation's SEC 10-Ks do: Niagara, Allegany and Buffalo Creek device, table, hotel-room, square-foot and parking counts, FY2004–FY2009. |
| **Pennsylvania** | 2 (via SEC) | no | **YES, via 10-K** | Not a tribal-compact state. Mohegan Sun Pocono appears only through the Mohegan Tribal Gaming Authority's 10-K. Included because the property is tribally owned; it is not an IGRA operation. |
| **Kansas** | 3 | no | no | Kansas State **Gaming Agency** (`kansas.gov/ksga`, not KRGC) publishes a 4-casino roster with addresses and hours. No metrics. |
| **Wisconsin** | **3** | no | no | **Confirmed by extraction this pass, contrary to expectation.** DOA Division of Gaming publishes Tribal Net Win, Tribal Gross Handle and Tribal Payments **in aggregate for all tribes**, FY2014–FY2024, as single-series bar charts (net win $1.16B FY2014 → $1.31B FY2024). No per-tribe breakdown anywhere. Not published here: a statewide aggregate is context, never an allocation. |
| **Florida** | 3 | no | no | **Re-checked this pass and still refused.** The Gaming Control Commission publishes pari-mutuel and cardroom data only. The Seminole revenue share appears solely in the Legislature's **Revenue Estimating Conference forecast** (EDR, 2026-01-09), which is a projection document with two rows labelled *Actual*, and its table has the same one-row column shift as the Michigan PDFs. Two readings of the same table give different values for 2023-24. Publishing a forecast as an actual is the specific error to avoid, so nothing was taken. |
| Minnesota | 3 | no | no | DPS publishes framework text only — 11 nations, 22 compacts, 20 casinos. No revenue sharing exists to report. |
| Nevada | 3 | no | no | NGCB reports by market area and covers only "nonrestricted gaming licensees", which excludes IGRA tribal operations. Wrong agency entirely. |
| Oregon | 3 | no | no | OSP performs regulatory functions under nine compacts and publishes no casino data. Compact **table limits** were recoverable from the compacts themselves — all 8 of this build's table-limit rows are Oregon. |
| Colorado | 3 | no | no | Verbatim: *"The two tribes, the Ute Mountain Ute Tribe and the Southern Ute Indian Tribe, are not subject to taxation and are not required to report their revenues to the State."* Confirmed empirically — the per-casino device PDF contains only Black Hawk / Central City / Cripple Creek. |
| Louisiana | 3 | no | no | LSP publishes monthly revenue for every licence class; zero tribal matches. The LGCB "Indian" section is **forms only**, though it does officially name the three tribal properties. |
| Iowa | 3 | no | no | IRGC facility licences are excursion boats and racetracks. Meskwaki, WinnaVegas, Blackbird Bend absent, as expected. |
| N. Dakota | 3 | no | no | AG gaming division inspects "the state's five Indian Casinos", publishes nothing per-tribe, refers to the Governor's Office. The 51 ND rows are compact authorisations, not regulator data. |
| S. Dakota | 3 | no | no | DOR gaming is Deadwood only. The 37 SD rows are compact authorisations. |
| N. Carolina | 3 | no | no | No state publication; the 8 NC rows are compact authorisations (EBCI). |
| Nebraska | 3 | no | no | Dept of Revenue gaming page is charitable gaming. **Still not fully confirmed** — the casino regulator host was unreachable, not 404. Worth one retry. |
| Wyoming | 3 | no | no | Pari-mutuel, historic horse racing, skill games, sports wagering. Zero tribal mentions. |
| Idaho | 3 | no | no | ISP has a Racing section only. No gaming division. |
| Massachusetts | 3 | no | no | MGC covers commercial licensees. The 20 MA rows are one compact authorisation and 19 environmental-review proposals (Mashpee Wampanoag). |
| Utah | 3 | — | — | No state gaming regulator exists. |
| Texas | 3 | — | — | **Verified negative**: the BIA compacts database state filter lists 28 states and Texas is absent. No Class III compact exists, so no regulator publishes anything. |

**Bottom line on the priority sweep.** Of the 18 states named in the brief —
WA, CA, AZ, NM, OK, MI, MN, WI, IA, LA, KS, CO, OR, ID, MT, NY, FL, CT — **every
one is now closed with a documented answer**. Exactly **two states publish
per-property revenue: Connecticut** (monthly, both properties, 1993–2025) and,
at tribe rather than property level, **New Mexico** (quarterly, 2002–2022).
Michigan is the only state where per-property revenue is *derivable* rather than
published, and only for four tribes and only for Class III electronic net win.

---

## Dead ends — documented so the next pass does not re-check them

**Access**

- ~~**`nmgcb.org` is behind Cloudflare** — 403 to both curl and WebFetch on every
  path.~~ **WRONG, corrected 2026-08-26.** `nmgcb.org` is not the agency any
  more; the domain lapsed and now serves a Spanish-language online-casino
  affiliate site. The root 403s and every *other* path returns that site's 404
  page with a full body. **NMGCB is at `www.gcb.nm.gov`.** The rest of the
  entry stands: the report PDFs are not on the agency host at all but in a
  RealFile widget. Year→folder GUIDs for **2002–2026** are now enumerable from
  the live page and from the widget API (see item 7 above).
- ~~**NM 2023–2025 quarters are NOT recoverable with what is on disk.**~~
  **RECOVERED 2026-08-26 — the four probes below were all against the wrong
  host.** They stay on the record because the failure shape is instructive:
  every one returned a plausible error (502/404) about a host that does not
  serve that API at all, and four such errors read as a closed door. The
  working endpoint is
  `https://klvg4oyd4j.execute-api.us-west-2.amazonaws.com/prod/GetWidgetFiles`,
  named in the site's own JavaScript. Original text follows.
  Probed that pass, four ways, all failed:
  `GET .../GetWidgetFiles?widgetId=…` → **502**;
  `GET …?acc=…&wid=…` → **502**;
  `GET …?accountId=…&widgetId=…` → **502**;
  `POST /GetWidgetFiles` (both param shapes) → **404 `Cannot POST`**.
  The endpoint is GET-only and rejects every parameter spelling recoverable from
  the saved manifest, and the folder GUIDs for 2023–2025 were never captured.
  **Getting past Cloudflare once, to read the current page's GUIDs, is the only
  route** — do not re-probe the API.
- **`web.archive.org` fails roughly half of all connections** with a 21s connect
  timeout, intermittently, then serves the identical request. That is a flaky
  path, **not** an edge block (PULL_DISCIPLINE rule 4 — an edge block is an
  instant refusal in under a second). Single stream, exponential backoff,
  checkpoint every result immediately.
- **`sbg.colorado.gov`** returns 403 to WebFetch but **200 to curl with a browser
  UA**.
- **WSGC rate-limits bursts** — after ~25 rapid requests curl returns `000`.
  Throttle.
- `pdftotext -layout` **scrambles** the NM tables and silently misattributes
  values to the wrong tribe. Use `pdftotext -table`.

**Text extraction — the recurring defect in this whole build**

- **`pdftotext -layout` shifts a column by one row whenever a table sets labels
  and values on baselines a point or two apart.** Confirmed in the **Michigan**
  payment tables, the **Michigan Annual Report**, the **Arizona** Gaming Status
  Report and the **Florida** EDR forecast. It is not rare and it is not visible
  in the output. **Read word positions and foot the result against the
  document's own printed totals**, or do not publish the table.
- **`wi_doa_Casino_Location_Map.pdf`** — casino names are drawn in a symbol font
  and extract as `?????`. Needs OCR; text extraction will never work.
- **Five of the 125 BIA environmental documents have no text layer at all**
  (`had_facility_specs = not_examined_no_text_layer` in
  `agent_nepa_document_log_2026-08-06.csv`). They are the only unexamined
  documents in that corpus and they need OCR.

**Sources that look right and are not**

- **`gaming.az.gov/sites/default/files/{2006..2014}_0.pdf`** — these look like
  ADG annual reports. They are **Arizona Office of Problem Gambling stakeholder
  reports**. No gaming data. Downloaded and confirmed; do not re-check.
- **Prior editions of the ADG Gaming Status Report are not on the live site.**
  Probing `Gaming%20Status%20Report%20<MMDDYYYY>.pdf` returns HTTP **200 with an
  HTML soft-404** for every date except the current one — a status code alone
  will mislead you here; check `content_type`. Wayback is the only route, and the
  archived filenames are **not** that pattern (`currentstatus7-6-15.pdf`,
  `Status of Tribal Gaming (6-30-22).pdf`, `GamingStatusReport020123_0.pdf`), so
  guessing URLs would have failed even against the archive. Enumerate.
- **CGCC `GGR24_080425.pdf`** — the filename suggests California gross gaming
  revenue. It is a **re-hosted NIGC national report** with 8 regional aggregates.
  Nothing Californian.
- **NM "Quick Facts" / Cumulative Quick Facts** — state licensees only
  (racetracks, non-profits). Tribal appears as one statewide line.
- **ADG's `tribal-contribution-breakdown` page** sounds like the per-tribe split
  that Arizona is missing. It is the **statutory distribution formula** — 12% to
  cities and counties of the tribe's choosing, 88% to the Arizona Benefits Fund,
  then 56/28/8/8 across education, trauma services, tourism and wildlife. No
  tribe is named and no amount is given. Retrieved and read this pass; do not
  re-check.
- **ADG quarterly `TribalContributions*` press releases** publish exactly one
  number — *"The tribes' combined contributions for the quarter ended March 31,
  2007 was $24,563,568"* — with no tribe split. Seven of them were retrieved from
  Wayback this pass and all seven were refused. Arizona's aggregation is
  statutory (A.R.S. § 5-601.02(H)(1)), not an oversight, so no amount of
  archive-digging will produce a per-tribe series.
- **A competitor's casino described inside an SEC 10-K is not data about that
  competitor.** The issuer is repeating trade press about a rival; the §302
  certification does not extend to it. 330 such windows were refused.
- `doa.wi.gov/Pages/AboutDOA/IndianGaming.aspx`, `wsgc.wa.gov/publications-and-reports`,
  `wsgc.wa.gov/sitemap.xml`, `michigan.gov/mgcb/tribal-gaming`,
  `ksgamingagency.ks.gov`, `krgc.ks.gov` — all 404. Live paths are in the state
  table above.
- `mn.gov/gcb` sits behind a ShieldSquare bot wall, and is the *charitable*
  Gambling Control Board anyway.

---

## The vendor comparison — QA in one direction only

`review/gaming_capacity_vendor_vs_official_2026-08-07.csv` (46 rows) and
`review/gaming_capacity_vendor_vs_official_distribution_2026-08-07.csv`.

**The comparison is QA in one direction only.** Per Elijah the vendor panel is an
internal fact-checking layer, never a published value and never a tie-breaker. So
the file does not grade the vendor. Where the two agree, confidence in **our**
official row rises; where they differ, it is a lead to re-check **our** row.

**The previous pass found 0 same-year overlaps. There are now 30** — 27 from the
SEC layer (Seneca Gaming Corporation) and 3 from the Arizona archive.

### Distribution of same-year differences (n = 30, exclusive bands)

| band, \|official − vendor\| as % of vendor | n | share |
|---|---:|---:|
| exactly 0 | 5 | 16.7% |
| 0 – 1% | 3 | 10.0% |
| 1 – 5% | 9 | 30.0% |
| 5 – 10% | 2 | 6.7% |
| 10 – 25% | 6 | 20.0% |
| 25 – 50% | 3 | 10.0% |
| over 50% | 2 | 6.7% |

**17 of 30 (56.7%) agree within 5%.** Quantiles of the signed % difference:
min −100.0, p10 −43.1, p25 −12.5, **median 0.0**, p75 +2.2, p90 +10.4,
max +23.5.

By metric, median |% difference|: `hotel_rooms` 0.0 · `table_games` 2.5 ·
`poker_tables` 3.0 · `gaming_machines` 4.5 · `gaming_square_feet` 7.0 ·
`parking_spaces` 43.1.

The bands are **exclusive and named that way**. An earlier version labelled them
`within_1pct`, `within_5pct`…, which reads as cumulative; a reader summing those
would double-count and a reader quoting one would understate agreement.

### Why Arizona contributed only 3 comparisons, and why that is not a data gap

Arizona is the one regulator publishing per-casino device counts, so it should
dominate this table. It does not, for a reason worth stating because it will not
fix itself:

1. **Metric-concept mismatch, not missing data.** The ADG table publishes
   **Class III** and **Class II** devices in separate columns. The vendor panel
   has exactly one device metric, `gaming_machines`, an all-class total. A
   Class III count and an all-class count are different quantities and comparing
   them would manufacture a disagreement. Script 92 derives a combined
   `gaming_machines` only where **both** components are present — and in the
   archived editions most casinos leave the Class II cell blank. For the
   *current* edition the document proves its own convention (the printed
   Class II total equals the sum of the stated values, so blank contributes
   nothing); **the archived editions have no printed total, so that inference is
   not licensed there and the total is not derived.**
2. **Blackjack tables are not `table_games`.** The vendor's `table_games` is a
   different aggregation, so those rows do not compare either.
3. **Facility names.** 10 of ~24 Arizona casinos per edition resolve to a Cedar
   property by exact name; the rest go to the review queue with candidates.

So the binding constraint on the Arizona comparison is **the review queue and the
metric vocabulary**, not retrieval. Ruling the 196 facility names is what unlocks
it.

### What the disagreements actually are

They are **not** randomly distributed. They cluster hard in **2004–2005**, the
years both Seneca properties were opening and expanding:

```
Seneca Allegany  gaming_machines   2004   official   185   vendor 1,500   -87.7%
Seneca Niagara   gaming_machines   2004   official 3,241   vendor 2,625   +23.5%
Seneca Niagara   parking_spaces    2004   official 2,900   vendor 5,100   -43.1%
Seneca Allegany  gaming_machines   2007   official 2,336   vendor 2,235    +4.5%
Seneca Allegany  gaming_machines   2008   official 2,330   vendor 2,235    +4.3%
Seneca Allegany  gaming_machines   2009   official 2,265   vendor 2,235    +1.3%
Seneca Niagara   hotel_rooms       2006   official   604   vendor   604     0.0%
```

Re-checking our own row, as the direction of this QA requires: the FY2004
Allegany figure of 185 is the **temporary** facility the 10-K describes as of
30 September 2004; the permanent Salamanca casino opened later. Our row is
correct **for its date**, and the vendor's is presumably a later floor carrying an
earlier year. **In every stable year the two agree closely.** That pattern —
tight agreement in steady state, wide divergence exactly where a property is
mid-build — is the most informative thing in the comparison, and it is a
statement about *dating*, not about either source's accuracy.

The one Arizona disagreement is the same shape: **Paradise Casino, 2006, poker
tables — official 0, vendor 5.5.** ADG prints `0`, and `0` is a count, not a
blank. Whether the Quechan property ran a poker room in February 2006 is exactly
the kind of question this file is meant to raise about **our** row, and it is
raised rather than resolved.

**No conclusion is drawn about the vendor panel's accuracy in either
direction.** 30 property-metric-years across two issuers is a first real test,
not a verdict. What turns it into one is now clearly identified, and it is not
retrieval: it is **ruling the 196 facility names** and **deriving a comparable
all-class Arizona device total**, both of which are described above.

The **16 nearest-year rows** span 3 to 18 years of gap, mix measurement
disagreement with real change in the property, settle nothing, and are labelled
`not_a_qa_signal_year_gap`. They are published so the near-misses are visible.
Their distribution is reported separately in the distribution file and must never
be pooled with the same-year rows.

---

## Review queue

`review/gaming_capacity_official_unresolved_2026-08-07.csv` — **311 rows**, blank
`YOUR_RULING`, project reconcile-queue format.

| n | reason |
|---:|---|
| 196 | `agent_facility_unresolved` — a regulator's casino name does not exactly match a Cedar property name (119 pre-existing + 77 from the Arizona archive) |
| 60 | `compact_statewide_pool_not_tribe_specific` — California licence-pool text, held out deliberately |
| 39 | `agent_tribe_unresolved:no_spine_match` — mostly MGCB's `Gun Lake` / `Gun Lake Tribe` labels for Match-E-Be-Nash-She-Wish, plus ADG's older tribe spellings |
| 11 | `agent_tribe_unresolved:refused_entity_class` — the two tribal-college resolutions above |
| 4 | `compact_authorization_no_tribe_and_no_state` |
| 1 | `ct_unknown_casino_label` — a `Mohegan Sun Prior Period Adj.` row in the CT feed, correctly refused |

The queue grew because the file grew, and that is the intended behaviour: an
Arizona casino whose 2006 name does not exactly match a Cedar property name goes
to a human, never to the nearest match.

**The facility-name rulings remain the highest-yield item and they are
actionable, not a dead end.** Following the `23g_gaming_duplicate_candidates.py`
pattern, each carries a `candidate_properties` column listing the tribe's
properties in that state:

```
Gila River - Lone Butte  ->  CCP-40500=Lone Butte Casino | VP-0231=Vee Quiva Hotel & Casino
                             | CCP-244900=Vee Quiva Hotel and Casino
                             | CCP-930600=Wild Horse Pass Hotel & Casino
```

**It rules nothing and merges nothing.** Two things remain visible in that one
line, and both are findings for whoever owns `gaming_facilities.csv`: the spine
appears to hold **Vee Quiva twice** (`VP-0231` and `CCP-244900`), and it has **no
row at all for Gila River's San Tan Mountain casino**, which ADG says opened
Jun-23 and runs 900 Class III devices.

---

## Rules honoured

- **Zero fabrication.** Verified mechanically this pass: **0 of 6,461 rows are
  missing `source_url` or `source_quote`**. Rows missing either are refused to
  the queue rather than trusted.
- **The promotion guard is enforced in code, not in prose.** `may_promote` is
  imported from `cedar_domain` and asserted at build time; every row carries a
  typed `measurement_type`; a `measurement_status` with no `MeasurementType` is
  refused to the queue rather than published untyped.
- **No second name matcher.** `resolve_entity` is imported from
  `code/33_apply_party_rulings.py`. What was added is a **refusal** on entity
  classes the source cannot be about — not a second matcher. Facility resolution
  is exact-name-within-state, or the tribe's sole property in that state, or
  refusal. There is no third tier, on purpose.
- **Aliases, not new properties.** `Mohegan Sun Pocono` (10-K) resolved to the
  existing `VP-0034 Mohegan Pennsylvania` as the tribe's sole property in that
  state. `Gun Lake` and `Gun Lake Tribe` are one tribe under two regulator
  labels and are queued as such, not split.
- **Class II/III mix stays a dated observation.** Arizona's Class II and Class III
  device columns are separate dated metrics; the combined `gaming_machines` total
  is derived, flagged and never treated as a property attribute.
- **Nothing deleted, nothing overwritten.** `gaming_property_capacity_history.csv`
  is untouched. Exclusions are columns (`exclusion_flag`, `exclusion_reason`),
  never deletions. Historical observations coexist: Mohegan Sun carries 6,425
  devices for FY2010 and 4,485 for FY2018 and both survive.
- **Not touched:** `gaming_facilities.csv`, `compacts.csv`, `compact_*`,
  `nigc_*`, `subawards.csv`, the identifier ledger, `admin_region*`,
  `resource_*`, `gaming_source_claims.csv`, `series_breaks.csv`.
  `code/01_build_entity_spine.py` was **not** run.

---

## Next, in value order

1. **Rule the 196 facility-name candidates.** This is now the binding
   constraint on everything Arizona, ahead of any further retrieval: 145
   verified per-casino rows for 2006 and 2012 are already on disk and only 66 of
   them land on a Cedar property. Two spine defects surface for free.
2. **Re-run `code/95_...py` then `code/97_...py`.** Both resume from disk and
   need no new decisions. It adds the remaining archived Arizona editions,
   including the 2015 `currentstatus*` set that sits eight years inside the
   vendor window.
3. **Rule the 11 entity-class refusals and the 39 no-spine-match tribes.** Small,
   mechanical, and it recovers ~50 Michigan, Montana and Arizona observations.
4. **Extend the SEC layer.** Mohegan filed 10-Ks through FY2022 and Seneca
   through FY2009; other tribal gaming issuers file with EDGAR and none have been
   swept. The guards in `code/96_...py` transfer unchanged.
5. **Michigan's other eight tribes.** Their 2% obligation arrives through Consent
   Judgments not held here. Obtaining those documents makes eight more tribes'
   Class III electronic net win exactly derivable, 1993 onward.
6. **OCR the five BIA environmental documents with no text layer**, and widen the
   NEPA sweep beyond the 125 documents already fully examined — 138 land
   decisions hold more, and it is the richest seam nothing else in the market
   carries.
7. ~~**New Mexico 2023–2025** — needs one Cloudflare-passing read of the current
   page to harvest three folder GUIDs. Do not re-probe the RealFile API.~~
   **DONE 2026-08-26 — and both halves of that sentence were wrong.**
   See `docs/BLOCKED_SOURCE_BYPASS_2026-08-26.md`.
   (a) There was no Cloudflare to pass: **`nmgcb.org` is no longer the agency's
   domain** — it lapsed and is now a Spanish-language online-casino affiliate
   site. NMGCB is at **`www.gcb.nm.gov`**, HTTP 200 to a browser User-Agent,
   `robots.txt` `Disallow:` (allow all). The folder GUIDs are in that page's
   markup.
   (b) The RealFile API SHOULD be re-probed, at the right host. The four 502s
   were against `api.realfile.rtsclients.com`, which serves `PublicFiles/…` and
   nothing else. The endpoint is named in the site's own SDK —
   `https://klvg4oyd4j.execute-api.us-west-2.amazonaws.com/prod/GetWidgetFiles`,
   GET, `{widgetId, folderId, rootFolderId, accountGUID}` — and it answers.
   **`rootFolderId` must match the widget**, or it returns 200 with `files: []`.
   **Recovered: 2023 Q1 – 2026 Q2, 14 quarters, 188 tribe-quarter rows, 14/14
   footing, $3,059,077,514.** Plus 91 monthly *Quick Facts* PDFs (FY2021–FY2026),
   a denser series Cedar did not hold at all. Staged at
   `review/nm_revshare_2023_2026_staged_2026-08-26.csv`; not merged.
