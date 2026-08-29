# State gaming regulators — the remaining-states pull

*2026-08-07. Script: `code/107_pull_remaining_states.py`.
Output: `data/clean/state_gaming_observations.csv`.
Queue: `review/state_gaming_unresolved_2026-08-07.csv`.
Raw: `data/raw/external/state_gaming/<st>/` with `_SOURCE_MANIFEST.csv` and md5s.
Codebook: `data/clean/codebook_master.csv`, dataset `14_state_gaming` (variables only).*

Companion to `docs/GAMING_CAPACITY_OFFICIAL_LOG.md`, which this file **corrects
in two places**, and to `docs/STATE_GAMING_FRAMEWORKS.md`, which it **extends by
one state**.

---

## What this adds, in one block

**15 states worked. 494 observations.**

| | |
|---|---:|
| Per-property device / table counts (Wisconsin, 7 dated editions) | **336** |
| Per-tribe payments (Wisconsin 88, New York 2) | **90** |
| Revenue rows (WI statewide series 32, AZ aggregates 3, **NY tribe-level derived 1**) | **36** |
| Facility-universe rows (NY 7, KS 4, NV 1) | **12** |
| **Documented absences, each with a verbatim quote and a typed kind** | **20** |
| Distinct Cedar properties keyed | **24** |
| — of which **new to the non-vendor official layer** | **22** |
| Distinct property × date capacity points | **113** |
| Distinct tribes keyed | **17** |
| Review-queue items (one per decision, not per occurrence) | **31** |

Every row carries `source_url` and a verbatim `source_quote`; **0 of 494 are
missing either**, asserted in the build before writing.

---

## The point of the exercise

Property-level gaming revenue is the binding constraint on everything. Residual
elimination against NIGC regional totals cannot start while exactly two
properties in the country carry a revenue figure. So the question put to every
state was, in order: does it publish per-property revenue; failing that,
per-tribe payments; failing that, counts; failing that, a facility list?

Two states answered better than the record said they would.

---

## ★ THE FINDS, in value order

### 1. New York publishes per-nation payments, and one of them inverts

**`code/107` now carries a THIRD state's tribe-level revenue.**

The New York State Gaming Commission's **2019** annual report prints this, and
no other edition of that report does — 2015, 2017, 2018, 2020, 2021, 2022, 2023
and 2024 were each checked:

> 2019 Regulatory Exclusivity Payment (25%)
> Mohawk $18,471,525.64
> Oneida $70,683,720.37
> Seneca \*
> \* - Current arbitration between the State of New York and the Seneca Nation

Three facts come out of four lines.

**a. Two per-nation payments, dated.** Recorded as `reported_payment`.

**b. The Seneca cell is a disclosed non-value, not a gap.** It is recorded as a
`documented_absence` with `exclusion_flag = withheld_by_source` and the
regulator's own stated reason. A blank here would be indistinguishable from a
figure nobody looked for; they are completely different facts.

**c. Mohawk's payment inverts to revenue, because the operative instrument is on
disk.** The Secretary-approved 2005 amendment to the Saint Regis Mohawk compact
states the rate *and* defines the base in its own words:

> "(d) State Contribution. In exchange and consideration for this exclusive
> franchise, the Tribe shall contribute to the State a portion of the proceeds
> from slot machines, **based on the net drop of such machines (money dropped
> into machines, after payout but before expense)**, according to the following
> schedule: in years one through four, eighteen percent; years five through
> seven, twenty-two percent; and **in years after seven, twenty-five percent**."

NYSGC's column header independently labels the 2019 payment 25%. Two legs that
agree, so `$18,471,525.64 / 0.25 = $73,886,102.56` of **Class III slot-machine
net drop, 2019** publishes as `exact_derived_revenue` /
`COMPACT_REPORTED_COUNT` / `TRIBE_LEVEL_REVENUE`.

Three limits ride on the row rather than waiting to be discovered: the concept
is **slot machines only** (no table games, no Class II, no non-gaming); it is
**tribe-level**, so `facility_id` is deliberately blank; and it is **2019 only**.

**Oneida is NOT derived, and the reason is the standard Michigan set.** MGCB
printed "2%" against all twelve of its tribes and script 94 derived for only the
four whose compact text was on disk, because *a regulator's summary table is not
the operative instrument*. New York splits the same way — see the mislabelled
compact finding below. `$70,683,720.37 / 0.25 = $282,734,881.48` is arithmetic
anybody can do. It is not evidence, and it is queued rather than published.

### 2. Wisconsin was mis-closed, and it is a per-property state

`docs/GAMING_CAPACITY_OFFICIAL_LOG.md` records Wisconsin as bucket 3 — *"No
per-tribe breakdown anywhere"* — on the strength of the Department of
Administration's aggregate bar charts. **That is true of DOA and false of the
state.**

The **Legislative Fiscal Bureau** publishes *Tribal Gaming in Wisconsin* every
two years. Seven editions are now on disk, 2013 → 2025, and they carry:

* **Table 1 — one row per Class III casino, with the electronic gaming devices
  and gaming tables at each.** The paper says so plainly: *"Table 1 lists the
  names and locations of current gaming facilities and the number of electronic
  gaming devices and gaming tables at each."*
* **Table 3 — lump-sum payments to the state, by tribe.**
* **Table 2 — statewide tribal Class III net revenue, 1992 forward.**

That is **168 per-casino rows across seven dated editions** — 23 to 25 casinos
per edition, each row carrying both a device count and a table count, so **336
observations**. Wisconsin moves from bucket 3 to
bucket 2 and joins Arizona as a state whose regulator-side record gives a
per-casino floor.

**Wisconsin still publishes no per-tribe revenue — and that absence is now
documented from the instrument rather than inferred from a missing table.**
Two quotes, and they say different things:

> "Tribes are required to submit annual independent financial audits of casino
> operations to the Department of Administration (DOA) and to the Legislative
> Audit Bureau (LAB). **These audits are confidential, and the revenue data for
> individual tribal operations may not be publicly disclosed.**"

> "It should be noted that **confidentiality provisions in each compact prohibit
> the disclosure of individual net win-based payments by tribe.**"

Wisconsin does not fail to publish the number. Wisconsin is forbidden to. No
amount of archive-digging will produce it, and a coverage table must not render
that the same way as a state nobody has checked.

---

## THE DEFECT THIS BUILD HAD TO SURVIVE

`pdftotext -layout` shifted **every single row** of **both** Wisconsin tables.
Measured, not assumed:

| | `-layout` | positional | truth |
|---|---|---|---|
| Ho-Chunk Wisconsin Dells, devices | 361 | **955** | 361 is Bad River's, one row above |
| Potawatomi Bingo Casino, devices | 111 | **2,609** | |
| Mole Lake Casino, devices | 1,110 | **308** | 1,110 is North Star Mohican's |
| **Red Cliff, lump-sum payments** | **$109,925,000** | **$0** | $109,925,000 is Forest County Potawatomi's |

The `-layout` reading books **$109.9M of Potawatomi's money onto Red Cliff**,
whose Legendary Waters casino runs 241 devices. Every row well-sourced, every row on the wrong
nation — AGENTS.md's containment defect in the costume it wore in Michigan and
Arizona, now confirmed in a fourth state's documents.

So nothing here is read linearly. The reader takes **word positions**, assigns
numbers to columns by **right edge** (right edges are stable across digit
counts; left edges are not), and **foots every numeric column against the
document's own printed totals**. An edition that does not foot is refused, not
published.

**All seven Wisconsin editions foot exactly, on both columns:**

| edition | as of | casinos | devices | tables |
|---|---|---:|---:|---:|
| 2025 | 2024-10 | 23 | 13,963 | 153 |
| 2023 | 2022-10 | 23 | 13,924 | 157 |
| 2021 | 2020-10 | 24 | 14,985 | 264 |
| 2019 | 2018-10 | 24 | 14,902 | 271 |
| 2017 | 2016-09 | 24 | 15,402 | 294 |
| 2015 | 2014-09 | 25 | 15,660 | 367 |
| 2013 | 2012-10 | 25 | 16,273 | 395 |

Table 3 foots to its printed `Subtotal Lump-Sum Payments` of $321,382,400, and
Table 2's 32-year series foots to its printed total of $31,670.1M. Three
independent footing checks, three passes.

**Two failures the footing check could not have caught, and what caught them
instead.**

1. **A table that is never found is never footed.** The caption changed wording
   mid-series — the 2013–2017 editions say *"Table 1: Indian Gaming Casinos"*,
   the 2019–2025 editions say *"Table 1: Class III Indian Gaming Casinos"*.
   Matching the later wording only dropped three whole editions **silently**,
   and the footing report showed seven green rows for four editions. Only the
   row count gave it away.
2. **Prose sliced by a table's x-bands looks exactly like data.** The first
   version of the New York roster reader returned **13 properties across 9
   nations** from a 7-property, 3-nation table — the paragraph after the table
   ran full width and every fabricated row was well-formed. The fix is a table-
   **end** test (a line starting left of the label column) applied *before* the
   bands are.

**And one table that looks shifted and is not.** NYSGC's compact roster reads,
linearly, as `St. Regis Mohawk Tribe → Yellow Brick Road`. That is wrong, and a
reader primed by Michigan will "correct" it in the wrong direction. Positionally
it is **hierarchical**: the nation label sits on its *first* casino's baseline
and its remaining casinos carry no label. The rule is **carry the label
forward**, not shift it. Under it Oneida keeps Turning Stone, Yellow Brick Road
and Point Place, which is correct.

---

## State-by-state

Verdicts: **per-property revenue** · **per-tribe payments** · **counts only** ·
**facility list only** · **nothing** · **structurally generates nothing** (the
framework produces no such record at all).

| State | Verdict | Per-property revenue | Per-tribe payments | Counts | What is published, and the evidence |
|---|---|:--:|:--:|:--:|---|
| **Wisconsin** | **counts + per-tribe payments** | no — **prohibited** | **YES** | **YES, per property** | LFB *Tribal Gaming in Wisconsin*, 7 editions 2013–2025. Per-casino devices and tables; per-tribe lump-sum payments; statewide net win 1992–2023. Revenue is barred by compact confidentiality clauses, quoted above. |
| **New York** | **per-tribe payments** (2019) | no | **YES (2019 only)** | no | NYSGC 2019 annual report: Mohawk $18,471,525.64, Oneida $70,683,720.37, Seneca withheld for arbitration. Mohawk inverts at the compact's stated 25% of slot net drop. Every other edition publishes the 7-property compact roster and nothing numeric. |
| **Arizona** | counts only (already held) | no — **aggregated by statute** | no | yes, per casino | Re-checked the "sleeper". ADG's FY2025 statutory report publishes **aggregate gross gaming revenue $3,033,358,250** and nothing per tribe, because A.R.S. § 5-601.02(H)(1) requires exactly that. The FY2025 Annual Report and the Compact Trust Fund report add no per-tribe figure. **Arizona is under-mined only in the archive, not in the live catalogue.** |
| **Louisiana** | **nothing — and the form is printed blank** | no | no | no | See below. The strongest documented absence in the sweep. |
| **Iowa** | nothing (tribal) | no | no | no | IRGC publishes rich per-property data — AGR, slot machines, table games, coin-in, monthly — for **commercial** licensees. Meskwaki, WinnaVegas and Blackbird Bend return **zero hits** across the July 2026 revenue report and the entire 1,191-line CY2024 annual report. |
| **Indiana** | nothing (tribal) | no | no | no | IGC publishes per-property win for 13 commercial casinos and offers it as **XLSX**. Four Winds South Bend / Pokagon Band is absent from the licensee list and every revenue report. Pokagon operates under IGRA, not an IGC owner's licence, so it never enters that universe. No Pokagon revenue-share figure is published. |
| **Mississippi** | **structurally generates nothing** | no | no | no | The Gaming Control Act created the Commission "to regulate dockside casinos". Choctaw returns zero hits across property data, monthly reports and regional reports. Note MS does not publish per-property *win* even for commercial operators — win is reported by region and denomination. |
| **Rhode Island** | **structurally generates nothing** | — | — | — | **No tribal gaming facility exists.** NIGC's national gaming-tribes list contains zero Rhode Island entries; DBR's gaming division regulates exactly two Bally's properties, both state video lottery. 25 U.S.C. § 1708, which governed IGRA's application to the Narragansett settlement lands, now reads "Omitted" in the Code. |
| **Nebraska** | nothing (tribal) — **host question resolved** | no | no | no | The prior record said "casino regulator host unreachable, not 404 — worth one retry". **It was a dead hostname, not an outage.** `ngc.nebraska.gov` and `racingandgaming.nebraska.gov` do not resolve; `racingcommission.nebraska.gov` → 301 → **`nrgc.nebraska.gov`, HTTP 200**. NRGC publishes per-property GGR and device counts for 11 **racetrack** casinos; zero tribal hits across three PDFs. Structural: IGRA facilities sit outside a racetrack-licensing regime. |

| **Kansas** | facility list only | no — **sealed** | no | no | KSGA's entire website is six pages; `/AnnualReport.htm`, `/Reports.htm`, `/Publications.htm` all 404. `Casinos.htm` gives name, address, phone and hours for all four casinos **plus each tribal gaming commission's address** — a real, if minimal, property universe. KLRD: *"Financial information concerning the operation of the four casinos is confidential. Under the existing compacts, the State does not receive revenue from the casinos, except for its oversight activities."* |
| **Colorado** | **structurally generates nothing** | no — **never collected** | no | no | Relocated and confirmed at `sbg.colorado.gov/tribal-casinos-in-colorado`: *"The two tribes, the Ute Mountain Ute Tribe and the Southern Ute Indian Tribe, are not subject to taxation and are not required to report their revenues to the State."* A second, **dated and archivable** instance sits on p.25 of the *Colorado Gaming Fact Book & Abstract 2024* — prefer it for citation. Colorado publishes nothing per-property for commercial casinos either. |
| **Nevada** | facility list only (1 property) | **no — held and sealed** | no | no | The most informative absence in the sweep. See below. |
| **North Dakota** | **structurally generates nothing** | **no — held and sealed** | no | no | N.D.C.C. § 54-58-02 seals every tribal gaming record submitted to the state. The AG's gaming page refers enquiries to the Governor's Office; the Governor's site has no compacts page. Per-tribe payments exist and are **flat and uniform** — $10,000 regulatory reimbursement and $25,000 contribution per tribe per year — so they carry **zero information about property size**. One rounded statewide aggregate ("roughly 3,300 Class III slot machines") exists, once, from 2022. The five properties are never named in any state document. |
| **South Dakota** | **structurally generates nothing** | no | no | no | SDCL § 42-7B-1 authorises limited gaming *"within the city limits of the city of Deadwood"*. Title 42 has no tribal chapter. `tribal|tribe|indian|compact` appears **zero** times in the entire FY2025 annual report. DOR's only acknowledgment tribal casinos exist is an age-limit sentence. Even Deadwood is aggregate-only. |
| **Minnesota** | **structurally generates nothing** | no — **no payment obligation exists** | no | no | See below. Confirmed from the compacts, the statute and the mandated report. |

### Minnesota — a documented structural absence, confirmed from the instruments

Minnesota was not to be reported as a gap, and it is not. It is confirmed on
three independent legs, none of them an assertion.

**1. The compacts are perpetual, and perpetuity is statutorily mandated.**
Shakopee Mdewakanton's 1989 video-games-of-chance compact, § 2.2 (transcribed
exactly, OCR artifact `o.r` included):

> "The State o.r the Community may, by appropriate and lawful means, request
> negotiations to amend, replace or repeal this compact. In the event of a
> request for renegotiation or the negotiation of a new compact, **this compact
> shall remain in effect until renegotiated or replaced.**"

§ 2.1 "Duration" contains no end date, no term of years and no expiration
trigger — read in full in two compacts, with the section headings of all 14 base
compacts checked. **Minn. Stat. § 3.9221 subd. 4** requires it:

> "A compact agreed to on behalf of the state under this section must contain:
> … (2) **a provision that in the event of a request for a renegotiation or a
> new compact the existing compact will remain in effect until renegotiated or
> replaced.**"

**2. There is no payments section to find.** All 14 original base compacts
(1989–1991) and six of the most recent amendments (2022–2025) were downloaded
and searched. `net win | gross revenue | gross gaming | revenue shar | remit |
contribut` returns seven hits across all fourteen, every one the identical
phrase *"requires that the proceeds be contributed to charity"* — a recital
about Minnesota's **charitable** gambling law, not a tribal payment. A
section-heading audit of the White Earth blackjack compact returns: Findings,
Duration, Jurisdiction, Regulatory Standards, Background Investigations,
Accounting and Audit, Amendments, Definitions, Effectiveness, Breach,
Retention. **No payments, fees, assessment or revenue-sharing section exists.**
The only money clause runs the *other* way — Shakopee § 6.11: *"The State shall
pay for any additional work performed by the auditors at the request of the
State."* Every "pay" hit in the 2022–2025 amendments is a machine **payout
percentage**. No payment to the state was introduced by any amendment through
2025.

**3. The mandated annual report is itself the proof.** Minnesota has published
a *Report to the Legislature on the Status of Indian Gambling in Minnesota*
every year since 1991. The **2025 edition is two pages**, and its entire
substantive content is: *"There have been no requests to renegotiate existing
compacts pursuant to the federal Indian Gaming Regulatory Act ('IGRA') during
2025."* The 2024 edition adds *"there is nothing to report"*. That is not an
agency neglecting to publish; § 3.9221 subd. 5 asks only for compacts negotiated
and prospective negotiations, because there is no money to account for.

Minnesota House Research supplies the contrast in as many words: *"IGRA
specifically prohibits states from imposing taxes or fees on Indian gambling,
except for fees that the tribe agrees to. … **In other words, states cannot
raise general revenue by taxing Indian gambling**"*, and then names **Connecticut**
— not Minnesota — as the state that negotiated a percentage in exchange for
monopoly.

**Blank Minnesota is correct.** Recorded as `no_payment_obligation_exists`, not
as unworked.

Two carry-forwards. **The AGED compact library covers 8 of 11 tribes** — Mille
Lacs, Prairie Island and Red Lake have no accordion and zero occurrences on the
page, so a page asserting 22 compacts publishes fewer. And
`age-sioux-community-*` files are **Upper Sioux**, not Prairie Island: the
1991-05-13 blackjack compact's caption reads "ON THE UPPER SIOUX COMMUNITY
RESERVATION". A filename-keyed ingest would misattribute them.

### Nevada — the state holds per-property tribal revenue and has contracted away the right to publish it

This is the sweep's most valuable structural finding, and it belongs in a
different bucket from every other blank in this file.

Nevada state-licenses exactly **one** tribal casino, under a licence type that
exists for it alone — `Nonrestricted-Indian`, licence `17698-01`, **Avi Resort &
Casino**, Laughlin (Fort Mojave Indian Tribe). It is the sole such row among
2,526 in the NGCB locations report, and it is **deliberately excluded from every
statistical product**: `Avi`, `Aha Macav`, `17698`, `Paiute`, `Indian` and
`Mojave` each return **zero** hits in the Nonrestricted Count Report workbook,
and the Gaming Revenue Report's Laughlin block counts 16 licensees — the
commercial ones.

But the number exists. The Washoe Tribe's 2018 amended compact requires it on
the **same form the commercial licensees file**:

> "For each Group I and Group II Tribal Gaming Operation, the Tribe shall submit
> to the Board a completed **'Monthly Gross Revenue Statistical Report'
> (NGC-31)** for each month of operation."

…and then seals it:

> "**The State shall maintain all audit and financial records obtained under
> this section, or any other section of this Compact, strictly confidential**,
> and shall not disseminate them to any member of the public for any purpose,
> except as required by Court order or applicable federal law."

NRS 463.120 makes the same records confidential as a matter of state law. **So
NGCB holds monthly per-property tribal win and cannot release it — barred by
statute *and* by compact.** A records request has no path.

Nevada compacts do carry payment obligations, but nothing is published against
them. Las Vegas Paiute 1994, § G: *"the Tribe agrees to pay Nevada a fee of one
percent (1%) of the gross revenue of the licensed gaming establishments located
on the Reservation."* A rate with no published payment inverts to nothing.

### The distinction this sweep is really about

**`never_collected` and `held_by_state_but_sealed` are both blank in a coverage
table and are entirely different facts.** Only one of them has a document in
existence. Knowing which decides whether any records strategy could ever work —
and here neither can be reached, but for different reasons, so a coverage table
that flattens them will send somebody after the wrong one. Every absence row in
`state_gaming_observations.csv` carries its kind:

| kind | states | means |
|---|---|---|
| `prohibited_by_instrument` | WI | The number is compiled and the compact forbids its disclosure |
| `held_by_state_but_sealed` | NV, ND, KS | The regulator receives it and statute or compact seals it |
| `aggregated_by_statute` | AZ | Published, but the statute mandates aggregation |
| `no_authority_to_compel` | LA | The regulator asks and cannot require an answer |
| `never_collected` | CO | The tribes are not required to report at all |
| `no_payment_obligation_exists` | MN | There is no payment, so there is no series |
| `outside_regulator_jurisdiction` | SD, MS, IA, IN, NE | The agency's authorising statute does not reach tribal gaming |
| `no_tribal_facility_exists` | RI | There is nothing to report on |

### Louisiana — the absence with a printed form behind it

Louisiana is the sweep's best-documented negative, because the Board says why in
its own words:

> "**This report contains no statistical information on tribal gaming.** The
> three (3) tribes authorized to conduct gaming operations on their tribal lands
> pursuant to IGRA class III gaming compacts are not required to pay any fees
> directly to the state and **cannot be required to provide the Board with any
> financial figures.**"

And it is stronger than a state that never asked. The LGCB **prints the
per-tribe form every year** — casino employees, Native American employees, wages,
vendor spend, parish contribution — plus a per-tribe, per-quarter
`TRIBAL PARISH CONTRIBUTIONS` table. Every cell reads **`Not Provided`**.
Checked across the FY2014-15, FY2017-18, FY2021-22 and FY2024-25 editions: blank
in all four. The Board asks; the tribes decline; the compacts say they may.

**One universe disagreement, queued not resolved.** LGCB names exactly three
gaming tribes. Cedar holds **four** Louisiana tribal properties, including
`CCP-657600 Jena Choctaw Pines Casino`. The Jena Band appears nowhere in the
report. Either Jena is outside the LGCB compact universe or the LGCB count is
stale; a source disagreeing with our universe is a finding, not a bug to smooth
over.

---

## Framework finding: Arizona runs a transferable slot market too

`docs/STATE_GAMING_FRAMEWORKS.md` presents the transferable machine allocation
as Washington's distinguishing feature. **Arizona has one as well**, stated by
ADG in its FY2025 annual report:

> "Currently, 16 Arizona Tribes operate 26 Class III casinos in the State.
> **Another six Tribes do not have casinos but have slot machine rights that
> they may lease to other Tribes with casinos (transfer agreements).**"

ADG names the six: Havasupai, Hopi, Hualapai, Kaibab Band of Paiute Indians, San
Juan Southern Paiute and Zuni. So the Washington rule generalises: **a tribe with
no casino and gaming-derived income is not a data error in Arizona either**, and
each lease is a Native-to-Native commercial relationship that federal data
cannot see. Model it as an event with two Native parties and a direction, not as
a property attribute — and an authorised or leased count is
`AUTHORIZED_MAXIMUM`, never `ACTIVE_FLOOR_COUNT`.

*(One of the six is `San Juan Southern Paiute`, which is exactly the spine
short-name collision AGENTS.md documents. Any Arizona allocation work must key
on `TRBF-SNJUAN-00` deliberately rather than by string.)*

---

## What is deliberately not published

* **Statewide aggregates are context, never an allocation.** Arizona's
  $3,033,358,250 and Wisconsin's 32-year net-win series carry
  `exclusion_flag = state_aggregate_not_allocatable` and
  `revenue_evidence = REGIONAL_GGR_CONTEXT`. They can bound a residual. They can
  never be mistaken for a property's revenue.
* **Cumulative windows never sit beside annual figures.** Wisconsin's Table 3
  leads with one column spanning 1999-00 → 2016-17. Following the Michigan
  precedent it is extracted, footed, and then given **its own metric name
  encoding the window** *and* `exclusion_flag = cumulative_window` — two
  independent guards, because a cumulative published beside annuals is a double
  count waiting to happen.
* **A payment is not revenue.** Wisconsin's lump sums are negotiated
  consideration with no stated rate and no stated base, so nothing is inverted
  and `revenue_evidence` stays `NO_REVENUE_OBSERVATION`.
* **The single-property attribution is proposed, never taken.** See the queue.

---

## Review queue

`review/state_gaming_unresolved_2026-08-07.csv` — **one item per DECISION, not
per occurrence**. The same casino appears in all seven Wisconsin editions;
emitting seven identical rows would ask a human the same question seven times
and make the queue look seven times more expensive than it is. Occurrences are
counted in `n_occurrences`.

The four items worth doing first:

1. **`single_property_attribution_proposed` — Akwesasne Mohawk Casino Resort.**
   `cedar_domain.may_attribute_to_single_property` needs all three of: one open
   property, a gaming-revenue base, a **verified** property count. The base is
   gaming revenue ✓. NYSGC's own compact table names exactly one Mohawk Class
   III casino ✓. Cedar holds **two** Mohawk NY properties — the casino and
   `CCP-43700 Mohawk Bingo Palace`, a Class II hall — so the count is not
   verified and the inference is **refused**. If Mohawk Bingo Palace is outside
   the Class III compact universe, **$73,886,102.56 attaches to a named property
   and New York becomes a per-property revenue state.** This is the highest-value
   ruling in the file.
2. **`compact_corpus_mislabelled_oneida`.** The corpus files
   `508 Compliant 2003.07.22 Oneida Nation Gaming Compact` and
   `508 Compliant 2021.08.20 Oneida Gaming Compact` are addressed to the
   Chairperson of the **Oneida Tribe of Indians of WISCONSIN** and amend the
   *Wisconsin* compact of 1991. They are filed under a New-York-sounding name.
   `cedar_domain.STANDING_DISAMBIGUATIONS` names Oneida NY vs Oneida WI
   explicitly; any compact-terms parse keyed on the filename has been attributing
   Wisconsin terms to New York. **A misfiled compact is worse than a missing one,
   because it answers.** (Bonus: those files state Wisconsin Oneida's net-win
   rate — 4.5% of net win from 2012, 5.5% above $350M net win — so a Wisconsin
   payment would be invertible if one were ever disclosed. It is not.)
3. **`ny_derivation_blocked_missing_instrument` — Oneida Indian Nation of New
   York.** Obtaining the operative New York agreement makes $282,734,881.48 of
   Class III slot net win publishable at tribe level.
4. **Facility-name aliases.** Regulator names that are not exact matches, each
   carrying a candidate list. Includes NYSGC's own misspelling `Akwasasne`, the
   LFB's `Ho-Chunk Gaming - Wittenburg` (for Wittenberg), and **`Point Place`,
   which Cedar appears not to hold at all** — the state names a compacted Oneida
   property absent from `gaming_facilities.csv`, the same shape of finding as
   Arizona's missing San Tan Mountain.

Tribe-level items carry candidate **spine entities** rather than candidate
properties, because that is the question actually being asked. Wisconsin's Table
3 says bare `Oneida` and bare `Potawatomi`; both are in `NAME_TRAPS`, both name
several nations, and both are correctly refused by `resolve_entity`.

---

## Dead ends and access notes — so the next pass does not re-check them

**Access**

* **`gaming.ny.gov` is Cloudflare-protected.** curl returns 403 "Just a
  moment…"; **WebFetch works**. The annual reports are served directly from
  `http://gaming.ny.gov/<year>-annual-report` — that path returns the PDF, not
  an HTML index.
* **`budget.ny.gov` is UNREACHABLE from this network** — `ECONNRESET` on both
  curl and WebFetch. That is **not** the same fact as "publishes nothing". The
  NY Division of the Budget financial plan is the one unexamined place a
  **Seneca-inclusive** per-nation series could live, and it deserves one retry
  from a different network before New York is recorded as 2019-only.
* **Nebraska's regulator hostname is `nrgc.nebraska.gov`.** `ngc.nebraska.gov`
  and `racingandgaming.nebraska.gov` do not resolve. The prior "unreachable"
  note is closed.
* `https://gaming.az.gov/sites/default/files/FY%2014%20Annual%20Report_0.pdf`
  returns **403** while the FY12 file at the same path pattern returns 200.

* **Minnesota's live AGED compact path is
  `https://dps.mn.gov/divisions/age/gambling/tribal-state-gaming-compacts`** —
  79 compact and amendment PDFs. The `divisions/age/Pages/indian-gaming.aspx`
  path in the older notes is dead (404).
* **South Dakota's tribal-relations host is `sdtribalrelations.sd.gov`**;
  `tribalrelations.sd.gov` does not resolve.
* **Colorado's tribal page has no `/tribal-gaming` path** (404). It is reachable
  only through a quick-link on `/gaming/limited-gaming`, at
  `/tribal-casinos-in-colorado`.
* **`sbg.colorado.gov` returns 403 to WebFetch and 200 to curl with a browser
  User-Agent** — the prior note is re-confirmed.
* **Both 1995 Colorado compacts are image-only scans with no text layer**
  (`pdftotext` yields 38 and 48 bytes). They need OCR.
* **`dor.sd.gov/search/` returns zero results for `tribal`, `casino` AND
  `compact`** — but "casino" demonstrably appears across the site, so **the
  site search index is broken and those nulls are evidence of nothing.** A
  search box that returns zero is not a source.

**Sources that look right and are not**

* **ADG `2006_0.pdf` … `2014_0.pdf` are Office of Problem Gambling stakeholder
  reports**, already recorded — re-confirmed from the reports index page, where
  they sit under the problem-gambling archive anchor. Do not re-check.
* **NYSGC `Seneca $605,733.00`** appears in a charitable bell-jar table and is
  **Seneca County**, not the Seneca Nation. That table is misaligned and its own
  TOTAL row does not foot.
* **OSC 2025 cash-basis `REGULATION INDIAN GAMING … 6,336,684.23`** is a fund
  name inside a *Temporary Loans Outstanding* schedule. It is a state
  regulatory-cost fund, not compact revenue, and it is not per tribe.
* **NYSGC tribal "certification counts"** are employee and vendor licences, not
  devices, and are badly misaligned in the text layer.
* **The Iowa revenue PDF is one of the worst text layers in the sweep** —
  property names and value columns are separated by many lines and interleaved.
  Nothing was taken from it and nothing should be without a positional read.
* **Indiana's monthly revenue PDF has the Location column shifted up one row**
  relative to casino names. Indiana publishes **XLSX** alongside; use it and the
  problem disappears.
* **The Kansas Governor's Budget Report FY2027 Vol 2 p.109 shifts by one row,
  and the naive read is wrong by a factor of eight.** `-layout` pairs
  *Tribal Gaming Regulation* with **$174,017**. Footed against the printed
  total, `174,017 + 8,561,392 + 1,360,621 = 10,096,030`, and the correct
  pairing by program scope is Racing Operations $174,017 (one historic-horse-
  racing facility opened December 2025), Expanded Gaming $8,561,392 (four
  state-owned casinos plus sports wagering), **Tribal Gaming Regulation
  $1,360,621** (FY2025 actual). The performance measures on the same page shift
  identically. Nothing from that page is published here, because a program
  expenditure is not a gaming metric — but the trap is recorded so the next
  reader does not fall into it.
* **The Colorado Fact Book's Employment table is badly scrambled by `-layout`**
  (county labels detached from values; "Total 747" landing above "Black Hawk
  1,374"). Do not extract from it without OCR or the `.xlsx`.
* **The Fort Mojave 1987/1990 Nevada compact's rate clause is OCR-destroyed** —
  the percentage has dropped out at `"(i) th.a gross rever:.ue"`. Re-OCR before
  quoting any rate from it.

---

## QA against the internal vendor panel — one direction only

Per standing policy the Casino City panel is an internal fact-checking layer,
never a published value and never a tie-breaker. So this compares **our** rows
to it and draws no conclusion about the vendor: where the two agree, confidence
in our row rises; where they differ, it is a lead to re-check **our** row.

Wisconsin's seven dated editions produce **35 same-year, same-property,
same-metric overlaps** — more than the **30** the entire previous build had.

| | |
|---|---:|
| n | 35 |
| exactly equal | 7 |
| within 5% | **28 of 35 (80%)** |
| median absolute difference | **1.7%** |

That is materially tighter than the previous build's 56.7%-within-5%, and it is
the strongest available evidence that the **positional read is correct**: an
independent source with a completely different collection method lands within a
couple of percent, property by property, across seven biennial snapshots. The
`-layout` read would not have survived this test for a single row.

The three widest gaps are all small Oneida convenience-store floors —
`CCP-860900` Oneida One-Stop Packerland (85 vs 114 in 2016), `CCP-697200`
Oneida Casino Travel Center (90 vs 110 in 2020) — where a handful of machines
moves the percentage a long way and where the LFB's October snapshot and the
vendor's date may simply be months apart. `CCP-656800` Ho-Chunk Wittenberg in
2022 (683 vs 786) sits over an expansion. All four are dating questions, not
extraction questions, and they are raised rather than resolved.

---

## A concurrency defect found while running this, and worth fixing centrally

`data/clean/codebook_master.csv` is shared, and it is being clobbered. Measured
today, from file mtimes and the backups on disk:

```
18:43:23  script 108 snapshots the file                     1,099 rows
18:43:42  script 107 snapshots the file                     1,121 rows
          (a third agent added `15_tribal_tax` in that 19-second window)
18:43:42  script 107 writes 107 + everything it saw
18:58:00  script 108 writes 108 + everything IT saw         1,174 rows
          -> `15_tribal_tax`   (22 rows)  GONE
          -> `14_state_gaming` (31 rows)  GONE
```

**Every script did the individually correct thing** — back up, re-read,
preserve what it saw, write. The failure is structural, and it is the same
shape as the four-pollers-per-host failure `PULL_DISCIPLINE.md` exists for: a
read-modify-write on a shared file is last-writer-wins, and no agent can see the
others.

Until it is fixed centrally, `code/107`'s codebook writer **restores**. It
compares what it is about to write against its own backup and puts back any
dataset that was present then and is absent now, printing what it restored. A
dataset vanishing between two runs on the same day is a clobber, not a decision
— a real deletion arrives with a script that removes it, not with a gap. This
run restored `15_tribal_tax`'s 22 rows, which belong to another agent.

The proper fix is a per-dataset codebook fragment (one file per dataset,
concatenated at build time) so two agents can never write the same bytes. Until
then, **any script that rewrites `codebook_master.csv` wholesale should adopt
the restoring merge**, and every one of them should keep taking its dated
backup — those backups are the only reason this was recoverable.

---

## Known gap in this build: retriever provenance

`data/raw/external/state_gaming/_SOURCE_MANIFEST.csv` covers **280 files, every
one with an md5**. It carries a `source_url` for the **19** files `code/107`
fetched itself and not yet for the **261** fetched by the reconnaissance passes,
whose URLs exist only in their transcripts.

That is disclosed rather than papered over, and it is not a blocker for anything
published here — every *observation* row carries its own `source_url` and
verbatim `source_quote`, and the observations are what ship. It is a
reproducibility gap in the raw tree only.

`code/107b_fill_source_urls.py` closes it: drop a
`_retriever_urls.csv` (`relative_path, source_url, fetched_date, note`) beside
the manifest and run it; `write_manifest()` then carries the URLs forward on
every subsequent run. **`UNKNOWN` is a legitimate value in that file and a guess
is not** — a plausible-looking wrong URL is worse than a blank, because it will
be believed, re-fetched, and whatever comes back will be treated as the same
document.

One file was **deleted rather than kept**:
`gaming.az.gov/.../FY%2014%20Annual%20Report_0.pdf` returns **HTTP 403** while
the FY12 file at the identical path pattern returns 200, and curl had written
the 5,642-byte HTML error body to a file named `.pdf`. A 403 body sitting in a
raw tree under a `.pdf` name is exactly the *check the status, not the file*
trap AGENTS.md records against bia.gov.

---

## Rules honoured

* **Zero fabrication.** Every published row carries `source_url` and a verbatim
  `source_quote`; the build asserts this before writing and refuses otherwise.
* **`resolve_entity` is the only name matcher**, imported from
  `code/33_apply_party_rulings.py`. What was added is a **refusal**, not a second
  matcher: entity classes a gaming regulator cannot be talking about (colleges,
  BIE schools, UIOs, the two financial-institution classes) are rejected and
  queued, and so is any resolution whose spine state disagrees with the
  publishing state.
* **`measurement_type` from `cedar_domain.MeasurementType` on every typed row**,
  with `may_promote` asserted at import for `AUTHORIZED_MAXIMUM`, `PROJECTED`,
  `ENVIRONMENTAL_REVIEW_COUNT` and `DERIVED_BOUND` against
  `ACTIVE_FLOOR_COUNT`. Nothing in this file is an authorisation; every typed
  row is a `REGULATORY_REPORTED_COUNT` or a `COMPACT_REPORTED_COUNT`.
* **Aliases, not new properties.** No property was created. Regulator names that
  do not match exactly go to the queue with candidates.
* **Nothing owned by another agent was touched.** `gaming_capacity_official.csv`,
  `gaming_revenue_bounds.csv`, `gaming_facilities.csv`, `nigc_*`, `compact_*`,
  `ca_gaming_*`, `wa_*`, `fl_*`, the ledger and the spine were **read only**.
  This build writes `data/clean/state_gaming_observations.csv`, its own review
  queue, its own raw tree, and one appended dataset block in
  `codebook_master.csv` (backed up first as `.bak_2026-08-07_pre107`, all
  pre-existing rows preserved).
* **Host discipline.** One stream per host, ≥1.5 s between requests, locks
  claimed in `logs/_HOSTLOCK_<host>.json`. `api.usaspending.gov` was not
  touched.
