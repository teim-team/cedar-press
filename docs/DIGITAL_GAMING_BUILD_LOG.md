# Digital gaming and loyalty — build log

*`code/119_build_digital_and_loyalty.py`, run 2026-08-07. Held back until the
compacts were parsed, because the compacts are what say who holds the rights.
They now do — 2,887 structured terms across 27 states — and reading them first
turned out to be the finding rather than the input.*

---

## WHAT WAS BUILT

```
data/clean/digital_gaming_relationships.csv     154 rows   94 tribes  15 states
data/clean/digital_gaming_revenue.csv        10,661 rows   16 tribes   3 states
data/clean/loyalty_programs.csv                  18 programmes        10 states
data/clean/loyalty_program_property.csv          48 programme-property rows
data/clean/codebook/16_digital_gaming.csv       105 variables (FRAGMENT)
review/digital_gaming_unresolved_2026-08-07.csv  35 items
data/raw/external/digital_gaming/                77 documents + _SOURCE_MANIFEST.csv (md5 on every row)
data/interim/119_run_summary.txt                 rewritten on every run
data/interim/119_mi_footing.csv                  378 month x metric footing tests
```

`code/62_no_regression_check.py` was run before and after. **No regressions**
either time. Nothing on the do-not-edit list was written: `gaming_facilities.csv`
and `nigc_declination_letters.csv` are read only, `codebook_master.csv` is
untouched and the codebook here is a **fragment** under `data/clean/codebook/`.

Every number below is reproduced from `data/interim/119_run_summary.txt`, which
the script writes on every run. Re-run it rather than editing a figure here.

---

## ★ THE FINDING: authorisation and operation do not overlap at all

| | tribes |
|---|---:|
| hold a digital gaming right in the parsed compacts | **81** |
| have a digital operation observed in a state regulator's file | **14** |
| **appear in both sets** | **0** |

Not "few". **Zero.** Eighty-one tribes are authorised for sports, internet or
mobile wagering by an instrument we hold, and not one of them turns up operating
in any regulator file this build read. The fourteen tribes that demonstrably
run online gaming — twelve in Michigan, two in Connecticut — have **no digital
authorisation anywhere in the 707-compact corpus.**

That is not two separate gaps. It is one structural fact with two faces:

**The states where tribal digital gaming actually happens do not authorise it
through the compact document we collect.** Michigan's twelve tribal operators
run under the **Lawful Internet Gaming Act (2019 PA 152)** and the **Lawful
Sports Betting Act (2019 PA 149)**, licensed by the MGCB. Connecticut's two run
under 2021 amendments to the Mashantucket and Mohegan procedures and the state's
master wagering licence. Michigan's eighteen compacts in Cedar yield **35
revenue-share rate rows, 15 base rows, 11 game-authorisation rows and zero
digital terms**; Connecticut's three yield **five terms, none digital.**

**The states whose compacts DO carry digital terms are mostly not the states
with digital operations.** Arizona's 21 tribes carry off-reservation mobile
wagering authority from the 2021 compact; Washington's 23 carry sports wagering
authority; New Mexico's 16 carry internet wagering language; North Dakota's five
and North Carolina's two carry on-Indian-lands mobile scope. None of those
states publishes a tribe-identified digital revenue series, and Arizona — which
publishes the most — publishes by **brand**, so its tribal licensees are
invisible in it.

**The one tribe in both sets is in both by contradiction.** The **Pokagon Band
of Potawatomi** is a licensed Michigan iGaming and online sports betting
operator, launched 2021-02-15, currently on the Strive platform. The only
digital term the compact corpus holds for Pokagon is in its **Indiana** compact,
effective 2021-07-02, and it reads `internet_wagering_authorized = prohibited`.
Same nation, two states, opposite facts, five months apart. Both are recorded;
neither is reconciled away.

**Therefore `launch_date` is populated on 24 of 154 rows and blank on 130, and
the blanks are a rule rather than an omission.** A right is not a launch. The
`compact_authority_cite` and `launch_date` columns exist separately so that no
downstream reader can collapse them, and `authorisation_observed` /
`operation_observed` make the collapse visible if anyone tries.

---

## THE SECOND FINDING: eighteen platform relationships have already ENDED

Michigan's monthly workbooks carry a `Platform Provider` row, and the provider
under a tribe's licence **changes**. Grouping the relationship on the provider
rather than on the operator surfaces eighteen relationships that are over:

| Tribe | former provider | current |
|---|---|---|
| Hannahville Indian Community | TwinSpires | Hard Rock Bet |
| Little Traverse Bay Bands of Odawa | FoxBet | bet365 |
| Sault Ste. Marie Tribe of Chippewa | Wynn | Caesars Horseshoe |
| Grand Traverse Band | William Hill | Caesars / WSOP |
| Lac Vieux Desert | PointsBet | Fanatics |
| Little River Band | Rush Street | BetRivers |
| Pokagon Band | Pala Interactive | Strive Platform |
| Nottawaseppi Huron | NYX Digital | NeoGames |
| Match-E-Be-Nash-She-Wish (Gun Lake) | Parx Interactive | BetPARX |

Each is a real commercial event — a tribe changing its technology vendor — and
none of it is visible in a property file, a compact, or a capacity observation.
**`cessation_date` is blank on all eighteen**, because MGCB publishes no end
date. It publishes an *absence* from a later sheet, which dates the change no
finer than a year, and the note on each row says exactly that rather than
inventing a day.

`launch_date` sits only on the FIRST provider era of each (tribe, product) pair,
because MGCB's "Initial date of Operation" is the **operator's** date and not the
vendor's. On later eras the field is blank with the reason in
`launch_date_basis`.

### NIGC independently corroborates four of them, and its characterisation wins

`nigc_declination_letters.csv` was read, never written. Filtering the 327
letters to contractors that are gaming-shaped or share a name token with a
provider we recorded leaves five, and four are direct hits:

- Grand Traverse — **American Wagering Inc.** (2020-09-02) = the William Hill
  entity, the provider MGCB's early sheets name.
- Hannahville — **Churchill Downs Interactive Gaming** (2020-08-07) = TwinSpires'
  corporate parent.
- Little River — **Rush Street Interactive MI, LLC** (2020-06-02).
- Little Traverse — **USBookmaking** (2020-07-28).

They are in the review queue, not merged. **A declination letter's legal
characterisation of a contractual role wins over trade-press terminology**, so
the letters must be read before anyone describes any of these vendors as
managing anything. `technology_provider` carries the vendor;
`operator_entity_id` remains the tribe on every row.

The other thirty-five letters these tribes hold name banks — PNC, Key Bank,
Wells Fargo, Devon Bank, Bank of America. Those are financing letters and say
nothing about a platform contract; they are counted and not raised.

---

## STATES PUBLISHING MONTHLY DIGITAL REVENUE

Four states, using the four-way coverage vocabulary so that a state nobody
checked never reads like a state that publishes nothing.

| State | | what it publishes | what is in this build |
|---|---|---|---|
| **Michigan** | `PUBLISHES` | per-operator monthly iGaming and internet sports betting: gross receipts, adjusted gross receipts, state tax/payment, total handle, plus the platform provider and initial date of operation | **5,670 rows, Jan 2022 – Jun 2026**, 12 tribal operators |
| **Connecticut** | `PUBLISHES` | per-licensee monthly online casino, online sports, retail sports and fantasy: wagers, patron winnings, cancelled wagers, promotional deductions, gross gaming, tax payment | **4,899 rows, Oct 2021 – Jun 2026**, 2 tribal nations |
| **Arizona** | `PUBLISHES`, but **by brand** | per-operator monthly event wagering, retail and mobile legs side by side | **91 rows, May 2026 only** — 4 tribe-attributable |
| **Florida** | `WITHHOLDS` | receipts only, and sports wagering only as a separately-labelled forecast | **1 explicit `NO_REVENUE_OBSERVATION` row** |

**Michigan is the single richest tribal digital dataset in the country and it is
free.** Cumulative tribal totals across the observed window, and these are
tribal operators only, never the three commercial Detroit casinos:

```
online sports betting handle          $ 9,948.7 m
gross gaming revenue                  $ 5,854.2 m
adjusted gross receipts               $ 5,010.4 m
state tax and payments                $ 1,035.8 m
```

Tribal iGaming adjusted gross receipts by calendar year: **$614.4 m (2022) ·
$799.6 m (2023) · $1,016.7 m (2024) · $1,313.5 m (2025) · $865.6 m (2026 through
June)**. Online sports betting AGR over the same years: $40.8 m · $68.4 m ·
$75.0 m · $163.6 m · $52.7 m.

Connecticut's tribal cumulative: **$7,647.5 m sports handle · $72,120.8 m online
casino amount wagered · $3,918.7 m gross gaming revenue · $2,641.0 m adjusted
gross · $1,376.2 m promotional deductions · $448.4 m paid to the State.**

### Every Michigan month is footed against MGCB's own printed total

A per-operator grid read out of a wide spreadsheet with merged headers is
exactly the shape of thing that produces a plausible wrong number. So the
aggregate columns are parsed too — kept out of the dataset, used only as a
check — and every (product, year, month, metric) cell is compared:

**270 footings pass. 0 fail.** 108 cells have no published total to foot
against (MGCB prints no aggregate for those metrics). The record is in
`data/interim/119_mi_footing.csv`.

Two independent corroborations came free. June 2026 iGaming gross receipts sum
to **$301,226,271.02**, MGCB's own aggregate cell to the cent; and online sports
betting handle for the same month sums to **$366,104,743.60** against the
$366.1 million MGCB states in its 21 July 2026 press release.

### Two traps caught inside Michigan and Connecticut

**Each MGCB workbook holds TWO year sheets and the ranges overlap.** The 2024
workbook carries 2024 and 2023; the 2023 workbook carries 2023 and 2022.
Parsing both **doubled every 2023 figure** — 1,260 duplicate rows, all of them
individually sourced, quoted, and wrong. A seen-sheet guard now refuses the
repeat. This is the same class of defect as `faads_transactions.csv` being a
strict subset of `faads_transactions_all_agencies.csv`.

**Connecticut labels two completely different measures `wagers`.** In a
sportsbook it is handle — money staked once. In an online casino it is coin-in,
which recycles on every spin and runs an order of magnitude larger: $72.1bn of
online casino wagers against $7.6bn of sports handle over the same window. They
are written under **different metric names** (`AMOUNT_WAGERED` vs `HANDLE`) so
that a `groupby(metric).sum()` cannot silently add them.

### Arizona publishes the most and attributes the least

ADG's Event Wagering Revenue Report prints one row per operator **brand** —
FanDuel, DraftKings, BetMGM, Caesars, bet365, Fanatics, PENN/ESPN Bet, Rush
Street, Bally, Golden Nugget, Sporttrade, Plannatech, and **Seminole Hard Rock
Digital**. Ten of Arizona's twenty event wagering licences are tribal and ten
are pro-sports franchises, and **the report does not say which licence each
brand sits under.** No ADG licensee list was found at `/event-wagering`,
`/event-wagering/licensees` or `/resources/reports`.

So thirteen brands are written with `is_tribe_attributable = no` and a blank
`tribe_id`, and each is a review item naming the concrete unblock. Only **Desert
Diamond Mobile** is keyed, to the Tohono O'odham Nation, because Desert Diamond
is that nation's own enterprise brand and Cedar's Arizona property universe
already carries Desert Diamond properties under it.

Arizona coverage is **one month**. The Event Wagering Report Archive on
`gaming.az.gov/resources/reports` is a Drupal AJAX view whose exposed year
filter returns the annual-report list rather than the monthly archive; only the
current month's PDF is present in the served HTML.

**The ADG report page is rotated 90 degrees**, and a naive text extraction of a
rotated PDF interleaves the columns into a grid that looks right and is not.
Every value is placed by its own coordinate — operator from the x-band, and the
Retail/Mobile leg *and* the metric from the y-distance to the report's own
printed `Retail` / `Mobile` header words. An operator that files only one leg
therefore lands in the correct leg instead of being guessed from a count.

**Arizona's Fantasy Sports Contest report names no tribal operator at all.** All
fourteen are commercial. Writing them into a Native dataset would pad it, so the
absence is recorded as a review item and no rows were written.

---

## LOYALTY PROGRAMMES — and why the count that matters is 11

**18 programmes across 10 states. 11 of them span more than one property**, over
48 distinct Cedar properties.

That is the analytic content. **A shared loyalty programme is evidence of
enterprise-level integration across properties** — one card, one ledger, one
marketing database across separately-licensed casinos — and it is observable
from a free web page when nothing else about the enterprise's internal structure
is.

| programme | operator | properties |
|---|---|---:|
| Status+ Rewards | Cherokee Nation (OK) | 11 |
| Rewards Club My Rewards Club | The Choctaw Nation of Oklahoma (OK) | 8 |
| W Club | Pokagon Band (MI) | 7 |
| Players Club Rewards | Grand Traverse Band (MI) | 3 |
| Potawatomi Rewards | Forest County Potawatomi (WI) | 3 |
| ACCESS Club | Saginaw Chippewa (MI) | 2 |
| Foxwoods Rewards | Mashantucket Pequot (CT) | 2 |
| Momentum | Mohegan Tribe (CT) | 2 |
| Winstar Rewards | The Chickasaw Nation (OK) | 2 |
| Salt River Rewards | Salt River (AZ) | 2 |
| Muckleshoot Rewards | Muckleshoot (WA) | 2 |

The remaining seven — Red Hot Rewards (Nottawaseppi Huron), Odawa Pure Rewards,
Turning Stone Rewards, Privileges Club (Pala), Club Osage, Pearl River Rewards
and Wind Creek Rewards — map to one Cedar property or to none, because the
programme page does not name the others. That is a fact about the page, not a
finding about the enterprise: Osage, Pearl River and Wind Creek all run several
properties and none of the three names them on the programme page in a form
this build would accept.

**`Rewards Club My Rewards Club` (Choctaw) and `ACCESS Club` (Saginaw Chippewa)
are the two names taken from an `<h1>` and both carry a review item.** The first
is visibly a concatenated banner and the label needs correcting by hand; its
eight-property map does not depend on it.

### The extraction rules, all of which cost recall on purpose

**Eligibility flags are set to `yes` on an explicit sentence and are otherwise
BLANK. They are never set to `no`.** A page that does not mention the sportsbook
is evidence about the page, not about the programme. Each `yes` additionally
requires an earning or redemption verb in the same sentence, and the sentence is
retained in `eligibility_quotes` — so "earn points on slots and table games" is
data and "the excitement never stops" is not.

**A property counts only where the page NAMES it**, and "names it" means either
the full property name appears, or every *distinctive* token of it does — a
token shared with the tribe's own name distinguishes nothing. A looser two-word
head match put **24 Choctaw properties on one page**, because every Choctaw
property name begins "Choctaw Casino" and so does every sentence about the
programme. That is the `core()`-folding lesson in a new place: a token that
appears in one name and not the other is never noise, and a token that appears
in both is never evidence.

**The programme name must come from the page's own `<title>` or `<h1>`.**
Searching the body finds the navigation menu, which is how a first pass produced
*"Facilities Weddings Reservations Rewards"* and *"Course Calendar Rates
Momentum"* — strings that are verbatim on the page and are nobody's programme.
Eight enterprises where the name appears only in body text are **name-only,
Tier B, in `review/`, and not in the dataset** — Sault Ste. Marie, Gun Lake,
Hannahville, Muscogee (Creek), Oneida (Wisconsin), Tohono O'odham, Puyallup and
Tulalip. Several of those are certainly real programmes with plausible body-text
candidates on the page (`Northern Rewards`, `Desert Diamond Rewards`, `EQC
Players Club`, `Connect Card Rewards`); the candidate is carried into the review
row so the hand pass is a confirmation rather than a search. Two names taken
from an `<h1>`
ship but carry a review item for confirmation, because the programme's existence
and its property map are separately evidenced and do not depend on the label.

A title segment that opens with a call to action is marketing prose, not a name:
`Join the Best Casino Loyalty Rewards | Status+ Rewards` names the programme in
its **second** segment.

**Tier names are almost entirely absent, deliberately.** A sentence-level scan
for capitalised words near "tier" returned `Please|Points|Copper|Premier` and
`Take|Osage|Casino|Hotel` — random capitalised words that look exactly like tier
labels. The tier labels carry little analytic weight, so recall was traded away
entirely: `tier_names` fills only from an explicit enumeration
(`tiers are X, Y and Z`).

**Six enterprises produced no loyalty page** — Bay Mills (MI), Ho-Chunk (WI),
Seneca (NY), Gila River (AZ), Seminole Hard Rock Tampa (FL) and White Earth's
Shooting Star (MN). Their site root either did
not return 200 or carried no loyalty-shaped link. Each is `NOT_FOUND` in the
review queue and **is not evidence that the enterprise runs no programme.**

---

## WHAT IS STRUCTURALLY UNOBTAINABLE

- **Which Arizona event wagering brand sits under which tribal licence.** ADG
  publishes revenue by brand and does not publish the licence holder alongside
  it. Until a licensee list is obtained, 13 brands' Arizona handle and receipts
  are permanently unattributable, and 10 tribal licences are invisible in the
  state's own revenue series.
- **Florida sports wagering as an actual figure.** EDR publishes receipts, not
  obligations, and prints sports wagering only as a separately-labelled forecast
  — `docs/FL_GAMING_BUILD_LOG.md` establishes this and it was not re-derived.
  The 2021 Compact requires the Tribe to give the State audited Net Win and, in
  the same instrument, lets the Tribe mark what it gives the State *"Trade
  Secret, Confidential and Proprietary"*. The State holds the number and does
  not publish it. The Seminole statewide mobile relationship is therefore
  recorded as **authorisation only, with `launch_date` blank** — the compact
  proves the right and nothing read here proves an operation.
- **Michigan 2021.** The MGCB workbooks on the live site go back to a 2023
  vintage carrying 2022; the January-2021 launch year needs a Wayback capture.
- **Cessation dates.** No regulator publishes the day a platform contract ended.
  Absence from a later sheet is the only signal and it dates the change to a
  year at best.
- **Per-property digital revenue anywhere.** Online gaming has no property.
  `facility_id` is blank on **all 154** relationship rows and that is correct,
  not missing: statewide mobile is a licence, not a building. Michigan's
  workbook names an associated bricks-and-mortar casino beside each operator and
  that name is carried in the row's `note` for context — never as the location
  of the revenue.
- **Tribal digital gaming in every other state.** New Mexico, Washington,
  Oregon, Wisconsin, North Dakota, North Carolina, Montana, Iowa, Mississippi,
  Nevada and Massachusetts carry compact digital terms and none of them was
  found to publish a tribe-identified digital revenue series. North Carolina was
  swept (`nclottery.com` root, `/about`, `/SportsBettingReports`,
  `/sitemap.xml`) and the site returns HTTP 200 with a 404 body for every path
  and serves no sitemap — a `NOT_FOUND` produced by a broken site, which is a
  fact about the site. Every other state in that list is **`NOT_CHECKED`.**

---

## ONLINE AND FLOOR REVENUE CANNOT BE ADDED, BY CONSTRUCTION

Every revenue row carries `revenue_scope`, constrained to
`ONLINE_CASINO_ONLY`, `ONLINE_SPORTS_WAGERING_ONLY`,
`RETAIL_SPORTS_WAGERING_ONLY`, `FANTASY_CONTESTS_ONLY` or
`NO_REVENUE_OBSERVATION`. **A physical casino GGR figure has no legal value in
that column**, and an assertion refuses the whole file if one appears. The
Michigan Detroit-casino series and the Connecticut Foxwoods/Mohegan slot series
sit on the same regulator pages and were deliberately not fetched.

Connecticut's on-reservation online casino licensees are recorded as **separate
relationships** from the same tribes' statewide digital licensees — `Mohegan
Tribe On-Reservation` and `Mohegan Digital, LLC` are two rows, as are `MPTN
On-Reservation` and `MPI Master Wagering License CT, LLC` — because the State
licenses them separately and they are different products. `mobile_on_premises`
and `mobile_statewide` carry the distinction: 11 rows on-premises, 48 statewide.

The three Detroit commercial operators and the Connecticut Lottery's retail
licensees are handled differently for the same reason. Detroit's are skipped
entirely. Connecticut's CLC rows are **written**, with `is_tribe_attributable =
no` and a blank `tribe_id`, because they share the licensee column with the
tribal ones and dropping them silently would make the State's own file look like
it was all tribal.

---

## ENTITY RESOLUTION — one resolver, two guards it does not carry

`resolve_entity` from `code/33_apply_party_rulings.py` is imported and never
re-implemented. Two guards sit around it:

**1. State agreement.** A state gaming regulator can only be publishing about a
tribe in its own state.

**2. Government class.** A gaming licensee is a government. Without this,
containment sends `Keweenaw Bay Indian Community` to **Keweenaw Bay Ojibwa
Community College** — a longer name, in the same state, in the spine. The fix is
not a new matcher: the *same* resolver is handed a government-only **view** of
the spine and returns the tribe. The eleventh instance of the containment
defect, and the eleventh time the recorded remedy — "restrict to
government-class rows" — was the one that worked.

`Soaring Eagle Gaming` resolves to an **Alaskan village** on containment
(`AKNF-VEAGLE-00`, on the token `Eagle`); the state guard refuses it. Three MGCB
strings no matcher can bridge carry documented aliases, each resolved to a
*tribe name* through the one resolver rather than to an ID by hand, and each
carrying its evidence:

- `Soaring Eagle Gaming` → Saginaw Chippewa — MGCB's own platform table lists
  Saginaw Chippewa against **GAN** and `playeagle.com`, and the workbook gives
  Soaring Eagle Gaming the same provider and the casino name Soaring Eagle.
- `Gun Lake Band of Pottawatomi Indians` / `Gun Lake Tribe` /
  `Gun Lake Band Tribal Community` → Match-E-Be-Nash-She-Wish Band.
- `Nottawaseppi Huron Band of Pottawatomi Indians` → Nottawaseppi Huron Band of
  the Potawatomi — **MGCB spells the same operator two ways on its own two
  pages**, against the same casino and the same provider.

MGCB spells its **vendors** inconsistently too — `Hard Rock` / `Hard Rock Bet`,
`Caesars Horshoe` / `Caesars Horseshoe`, `Golden Nugget Casino` / `Golden Nugget
Online Gaming`. Provider eras group on an eight-character normalised head, which
collapses all three pairs and separates every genuinely distinct vendor. The
verbatim spellings are kept on the row and the variants are named in the note.

---

## PULL DISCIPLINE

37 hosts, each claimed in `logs/_HOSTLOCK_<host>.json`, worked sequentially at a
1.6 s gap, single-shot with **no retry loop**, idempotent skip-if-present, and
released on completion. 77 documents; 75 returned 200, 2 returned nothing and
are recorded as such. md5 on every manifest row.

`files.usaspending.gov`, `api.usaspending.gov`, `apps.nd.gov`,
`www.treasurer.nd.gov` and `www.nigc.gov` are refused **in code** by a
`FORBIDDEN_HOSTS` set, not by intention.

**`web.archive.org` was NOT polled.** It is held by an active lock claimed
4.5 hours before this run. The PID is dead, but PULL_DISCIPLINE rule 2 allows
takeover only after **six** hours, so the Wayback leg — historic loyalty pages
for programme change over time, and the Michigan 2021 workbooks — was **appended
to that lock's queue** and this build stopped. That is the whole of rule 1: a
second poller is worse than a deferred job.

`save_manifest()` merges with the file on disk rather than replacing it. A
`--skip-fetch` run has an empty in-memory manifest, and writing that over the
file erases the md5 of every document already retrieved — which it did once,
before the merge was added.

---

## A DEFECT WORTH RECORDING BECAUSE IT WAS INVISIBLE

A patch inserted a literal **`0x08` backspace character** into a regex, so
`re.match(r"...find)\x08", ...)` silently never matched and a marketing-prose
filter did nothing. The terminal rendered the backspace by *erasing the
preceding character*, so `grep`, `sed` and `inspect.getsource` all displayed the
line as correct. It was found only by printing `repr()` of the source line.

The rule: when code that reads correctly behaves as if it were absent, print
`repr()` of the source, not the source.

---

## KNOWN UNEXTRACTED

Written down because a gap nobody records looks identical to a gap nobody found.

- **Michigan 2021** — the launch year. Needs Wayback; queued.
- **Arizona before May 2026** — the monthly archive is behind a Drupal AJAX
  view. A direct file-name pattern for the historical `EW Website Report-*.pdf`
  would unlock roughly 55 months at one request each.
- **Connecticut's physical slot series** was deliberately not fetched. It is on
  the same portal (`i6ts-ib7c`, `xrid-g2yu`, `sz5u-xk5e`) and belongs to the
  capacity layer, not here.
- **Tier thresholds and earning currency** are empty on all 18 programmes. Both
  are usually in a table image or a PDF, neither of which this build reads.
- **Loyalty history.** No Wayback capture was taken, so `start_date` is blank on
  every programme and `current_status` is `observed_active` as of one
  observation date. A snapshot only becomes an observation when it establishes a
  meaningful value or change; none was available to compare against.
