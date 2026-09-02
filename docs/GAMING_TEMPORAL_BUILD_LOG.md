# Gaming — the time dimension

*Built 2026-08-05; extended and corrected 2026-08-06. Script:
`code/23f_gaming_temporal.py`. Audit: `code/35_coverage_audit.py`. Codebook:
`code/41_build_codebooks.py`. Evidence files, one per research sweep:
`data/raw/external/gaming/facility_opening_research_<date>.csv`.*

**What changed on 2026-08-06**

1. **75 of the 93 researched facilities were not actually in the file.** The
   2026-08-05 run was killed after writing its evidence CSV (19:05) but before
   re-running the build (18:55). Re-running applied them: exact 558 → **617**,
   bounded 44 → **77**, undated 148 → **56**. Three further sweeps the same day took
   it to **635 / 90 / 23**.
2. **`not_gaming_commencement` was over-claimed** and is now reserved for
   verified rows only (§2).
3. **Four post-1979 property/gaming conflations found and ruled**, including
   Lake of Isles — Foxwoods' *golf course* — which had been publishing as
   `gaming_commenced` (§2).
4. **`open_date` is not a uniform ISO column** and the codebook said it was
   (§2).
5. **The `open_date` convention is now stated in the codebook**, which
   previously described the column as `Date.` (§8).
6. **Coverage reaches 1905–2025**, up from 1905–2018, and the `SOURCE_CEILINGS`
   entry was **retired** rather than raised — the 2018 ceiling belonged to the
   inherited vendor column, not to the dataset, and what remains is ordinary
   unfinished work that the audit should be free to report (§5).
7. **The undated rows are substantially DUPLICATES, not missing research** —
   49 of 56 carried `duplicate_risk = 1`, and researching them returned dates
   the file already held on a twin row. New review queue (§7.5).
8. **Many rows do not describe a real, distinct property** — a golf course, a
   grocery brand, a phantom travel plaza, a three-nation name collision, a
   Nevada row holding an Idaho casino. Second review queue, **17 rows**
   (§7.5b–d).
9. **The rebuild keyword rule misfires in BOTH directions** and was guarded
   (§2). It read researchers' *disclaimers* ("the ORIGINAL opening, not the
   2012 rebranding") as claims.
10. **Two well-sourced dates were deliberately NOT recorded** because the rows
    they would land on are misidentified (§7.5c), and **two rows were retired as
    convenience stores** (§7.5d).
11. **Researching undated rows found a defect on an already-DATED row** — the
    Northern Lights date is probably a rebuild (§7.6b).

> **§9 (2026-08-06, session 3) supersedes parts of what follows.** The undated
> pool fell from 23 to 9 with **no new dates**, because the rows were
> duplicates the roster had already disclosed in its own `notes` column. §7.6
> and §7.6b are resolved there; §7.5b's readings of **MidJim ×2** and
> **Seminole Nation Travel Plaza** are **withdrawn** there (§9.5) — a 2026 web
> page cannot refute a vendor record that closed in 2003. Read §9 before
> treating anything below as current.

Companion to `GAMING_BUILD_LOG_2026-08-05.md`, which built the layer this one dates.

---

## The finding, stated plainly

`code/35_coverage_audit.py` reported:

```
gaming_facilities        no usable date column  (2 file(s))
```

**That report was true of the audit and false of the data.** Both files were
already dated. Neither carried its dates under a name the audit's `DATE_COLS`
list recognised:

| File | Date columns it actually had | Fill |
|---|---|---:|
| `gaming_facilities.csv` | `open_date` | 559 / 774 (72%) |
| | `close_date` | 148 / 774 |
| | ten `<metric>_observed_date` columns | 96–409 each |
| `gaming_facility_metrics.csv` | `observation_date` | 64,181 / 65,223 |
| | `observation_period` | 1,042 / 65,223 |

`DATE_COLS` held `action_date`, `filing_date`, `decision_date`, `effective_date`
and plain `date` — the vocabulary of **transaction** files. Matching is exact on
the lowercased name, so `date` never matched `open_date`. Gaming is the
project's only **entity** dataset and its only **measurement** dataset, and both
shapes date themselves differently:

- an entity file is dated by a **lifespan** — `open_date`, `close_date`;
- a measurement file is dated by an **as-of date** — when the count was taken.

Neither looks like `action_date`. The audit was measuring the wrong thing and
saying so honestly, which is why the defect was findable at all.

**So the first fix was one line in a list, exactly as suspected.** Everything
below is the second problem, which the naming bug had been hiding.

---

## 1. `as_of_date` — the metrics file was already 100% datable

`observation_date` and `observation_period` are **exactly complementary**:

```
both populated      0
observation_date    64,181
observation_period   1,042   (a bare four-digit fiscal year, 1994–2026)
neither                  0
```

So a single derived column reaches every row:

| `as_of_date_basis` | n | `as_of_date_precision` |
|---|---:|---|
| `source observation_date` | 64,181 | `day` |
| derived from `observation_period` — the source states a fiscal year only, so month and day are not claimed | 1,042 | `year` |

**`as_of_date` is populated on 65,223 of 65,223 rows.** Range **1994–2026**.

This is the column the dataset could not be sold without. *"1,200 gaming
machines"* is not a fact; *"1,200 gaming machines as of 2019-07-01"* is. The
1,042 year-only rows are precisely the dollar rows — gaming revenue and payments
to government — which are reported by fiscal year and never by day. Recording
them as `1994-01-01 / precision=year` says so; recording them as `1994-01-01`
alone would invent a January date for every one.

**The facility file needed no repair here.** All 2,243 point-in-time metric
values carried on facility rows (machines, tables, seats, square footage, rooms,
parking, employees, restaurants) already have their own `_observed_date`:

| metric | values | with no as-of date |
|---|---:|---:|
| all ten capacity metrics | 2,243 | **0** |

---

## 2. Opening dates look far more precise than they are

The 447 ISO opening dates inherited from the Casino City Tribal Property List
do not have the day-of-month distribution of real dates:

| day of month | n | share | expected |
|---|---:|---:|---:|
| **31** (147 of them `12-31`) | 150 | 33.6% | ~3.3% |
| **15** | 148 | 33.1% | ~3.3% |
| everything else | 149 | 33.3% | ~93% |

`YYYY-12-31` is that source's year-precision placeholder and `YYYY-MM-15` is the
mid-month convention. **Two thirds of the opening dates in this dataset were
placeholders wearing day precision.** The same pattern is in `close_date`
(day 15 = 44%, day 31 = 15%).

The build therefore derives `open_date_precision` rather than assuming it, and
widens `open_date_not_before` / `open_date_not_after` to the interval the source
actually supports. **The source value is never modified** — `open_date` still
reads `1992-12-31`; the interval beside it reads `1992-01-01 … 1992-12-31` and
the precision column reads `year`.

Resulting honest precision of the exact dates:

| precision | n | why |
|---|---:|---|
| `day` | 185 | a real day is stated |
| `year` | 288 | `YYYY-12-31` placeholder, bare `YYYY`, or a hand-researched year |
| `month` | 162 | day-15 placeholder, or a hand-researched month |
| `decade` | 1 | the source says `1980s`; classed `bounded`, not `exact` |

*(Counts as at 2026-08-06, after both research sweeps. The proportions are what
matter and they did not move: the placeholder problem is in the inherited 447,
and hand research adds honestly-graded precision on top of it.)*

The cost is that a genuinely-Dec-31 or genuinely-15th opening is now recorded as
less precise than it is — roughly one row in each bucket against ~290 rows of
false precision removed. Precision over recall.

### `open_date` is not reliably the *original* opening

A consistency check against the capacity panel found **27 facilities whose
stated opening date is LATER than an observation of the same property already
operating**:

| Facility | stated `open_date` | observed open by |
|---|---|---|
| Apache Casino Hotel | 2012 | 2001-09-01 |
| Blue Star Gaming and Casino | 2010-10-15 | 2001-09-01 |
| San Pablo Lytton Casino | 2003-10-15 | 2001-09-01 |
| Choctaw Casino – McAlester | 2009 | 2001-09-01 |
| Border Casino | 2017 | 2010-11-03 |
| …22 more | | |

The source's `Open Date` is therefore dating the **current building or a
re-opening** on these rows, not the original opening. Anyone charting "casino
openings by year" off this column is partly charting rebuilds. Flagged
`open_date_postdates_observation = 1`, with `observed_open_by` carrying the
contradicting observation. Nothing was corrected — both values are source values
and there is no evidence for which one to prefer.

The same defect in mirror image: **4 facilities carry a closing date earlier than
their opening date** (Choctaw Durant, Creek Nation Bristow, Seminole Nation
Casino, The Artesian). Almost certainly a predecessor building's closure paired
with a replacement's opening. Flagged `close_date_precedes_open_date = 1`.

### `open_date` was silently meaning two different things

A date can be exact and still be about the wrong event. `open_date` was carrying
both **"gaming commenced here"** and **"this property opened"**, which are not
the same event on a site that existed before it hosted gaming. Pooled, they
corrupt any *"tribal gaming since 19xx"* series at the left tail — and corrupt it
**invisibly**, because the basis column says the date is exact and it is; it is
just exact about something else.

`open_date_event` now names the event on every row that carries a stated date:

| `open_date_event` | n | meaning |
|---|---:|---|
| `unspecified` | 446 | Casino City publishes an `Open Date` for a gaming property but **does not state which event it marks**. Not inferred here. |
| `gaming_commenced` | 162 | Indian Gaming Dataset (a source that codes dated *gaming* opening events with a per-event URL, so the event is the source's own subject), plus hand research against a source describing a casino opening to the public. |
| `property_opened` | 9 | The cited source dates the property, or the current building, not the commencement of gaming. |
| `not_gaming_commencement` | 1 | Verified not a gaming date (Crosby Lodge, below). |

**`unspecified` is the majority and it is not a defect to be cleaned.** It is
what the source supports. Splitting `open_date` into `property_opened_date` and
`gaming_opened_date` was considered and **rejected**: it would force 446 rows
into one column or the other on evidence that does not exist, replacing a
disclosed ambiguity with an undisclosed guess. Naming the event, and admitting
when it is unknown, is the honest structure.

#### Crosby Lodge — verified, and it is not a gaming date

`CCP-1189200` carried `1905-06-07` at *day* precision, `basis=exact`.

Verified against the operator's own site
([crosbylodge.com, Internet Archive 2001-04-28](https://web.archive.org/web/20010428005337/http://www.crosbylodge.com/)).
Crosby Lodge at Sutcliffe on Pyramid Lake is a lodge, grocery store, snack bar
and bar. The page advertises lodging, fishing tackle, propane, gasoline, an RV
park and fishing derbies. **It contains no occurrence of the words casino, slot,
gaming or bingo.** It states:

> *"Our lodge has been in the family since 1896."*
> *"We have been your hosts since 1970."*

Neither is 1905 — so **what `1905-06-07` marks is not established either**, only
that it is certainly not the date gaming commenced. Classed
`not_gaming_commencement`, with the URL and quote on the row. The date itself is
retained unchanged.

*(Separately worth a ruling: Crosby Lodge is a family business on the Pyramid
Lake reservation. Its `tribe` value looks like a location attribution rather than
ownership. Out of scope here — noted for the reconcile queue.)*

#### Seneca Gaming and Entertainment – Irving — pushed as far as the evidence goes (2026-08-06)

`CCP-43500` carries `1970-12-31` (→ year precision). **Still no source states an
opening date, and after this session's work that is now a supported claim rather
than an unfinished one.**

What was added: the Seneca Nation runs its Class II halls through *Seneca Gaming
& Entertainment*, while the Class III casinos sit under *Seneca Gaming
Corporation*, *which is an SEC registrant* (CIK `0001296785`) because it issued
public notes. Its **Form S-4 filed 2004-07-23** describes the Nation's other
gaming operations directly:

> *"The Nation, through its wholly owned business enterprise, Seneca Gaming &
> Entertainment, operates a Class II gaming facility located on the Nation's
> Territory in Irving, New York. For the fiscal year ended September 30, 2003,
> the Irving Class II facility generated $25.5 million in net revenue and income
> from operations of $11.9 million."*

— [SEC S-4, 2004-07-23](https://www.sec.gov/Archives/edgar/data/1296785/000104746904024134/a2140167zs-4.htm)

That is a primary filing and it **proves the hall was operating by 2003-09-30**.
It says nothing whatever about 1970. The current `senecagames.com` (fetched
2026-08-06) still lists Irving, Salamanca and Oil Spring and states no opening
date anywhere on the page.

So the row now carries the corroboration in `open_date_event_basis` — recording
**how far verification got**, which is more useful to a subscriber than a bare
"not established". The lesson generalises and is worth reusing: **a tribal gaming
enterprise with public debt is an SEC registrant, and its filings describe the
tribe's *other*, non-registrant gaming operations in plain narrative.** That is a
primary-source route into small tribal halls that have no web presence at all.
Five of this dataset's opening dates already come from SEC filings.

#### The detector, and an over-claim corrected (2026-08-06)

`open_date_predates_tribal_gaming_era = 1` where a stated opening date falls
before **1979** — the year the Seminole Tribe opened the Hollywood high-stakes
bingo hall that produced *Seminole Tribe v. Butterworth* and, through it, IGRA.
The threshold is stated rather than tuned. It now fires on **4** rows: Crosby
Lodge (1905), Seneca Irving (1970), Pala Mesa Resort (1961) and Singing Hills
Golf Resort at Sycuan (1956) — and on nothing else.

**The rule used to over-claim, and that is fixed.** A row that tripped the
detector with no source quote was published as `open_date_event =
not_gaming_commencement`, on the strength of the threshold alone. That asserts a
negative the threshold cannot carry: 1979 is the first year of **high-stakes**
tribal bingo, *not* the first year of tribal gaming of any kind, and small
charitable bingo halls predate it. Seneca Irving at 1970 is exactly the case
where the difference matters.

`not_gaming_commencement` is now **reserved for rows actually verified against a
source** — one row, Crosby Lodge. A row that is merely *implausible* as a gaming
date stays `unspecified` and carries the flag, with a basis string that opens
`NOT INDEPENDENTLY VERIFIED` and says in as many words that the date is unlikely
but not proven to mark gaming commencement. The flag column already carried the
whole signal; the event column was adding a claim to it.

#### Four post-1979 conflations the detector cannot reach

The 1979 detector only sees the left tail. Auditing the 59 hand-researched rows
found the same property-vs-gaming conflation **above** the threshold, where no
automatic rule can see it, and the row's own evidence string already disclosed it:

| Facility | `open_date` | What the row's own evidence says |
|---|---|---|
| **Lake of Isles (Foxwoods Golf)**, `VP-0002` | 2005 | The cited quote is *"Since opening in 2005, Lake of Isles has consistently been ranked as one of the top **golf facilities** in the country."* It is Foxwoods' golf course. Gaming at Mashantucket began 1986 (bingo) / 1992 (casino). **This is the clearest surviving instance of the Crosby Lodge defect on a modern row.** |
| Shoshone-Bannock Casino Hotel, `VP-0392` | 2019-02-05 | *"CURRENT BUILDING ONLY … the same article says [it] replaces the older, detached casino."* |
| Foxwoods Casino, `VP-0037` | 1992-02-15 | *"Dates the casino opening, not the 1986 bingo-hall predecessor."* |
| Soboba Casino Resort, `VP-0051` | 2019-02-20 | *"replaced the original 1995 Soboba Casino on a different site, which was already operating by 2000-10-17."* |

All four were publishing as `gaming_commenced`. They are now `property_opened`,
ruled one at a time in `RULED_EVENT` against the quote already on the row.

#### The keyword rule misfires in BOTH directions

Adding the Oklahoma batches exposed the mirror-image bug. The rule flips a
hand-researched row to `property_opened` when its note contains `rebrand`,
`replacement building`, `relocat`, `new building` or `successor` — but
**researchers mention a rebuild precisely in order to rule it out**:

> *"The Feb 1987 date is the **ORIGINAL** opening as a high-stakes bingo hall,
> **not** the 2012 renovation/rebranding."* — Muscogee Okmulgee / One Fire

> *"The 1986 date is the original facility opening, **not** the Yaamava' rebrand
> or the hotel."* — San Manuel

Both were published as `property_opened`. **A substring scan read the disclaimer
as the claim** and demoted two correct gaming-commencement dates — one of them a
1986 pre-IGRA bingo hall, exactly the kind of row §2 warns must not be
"cleaned". A negation guard now suppresses the flip where the note asserts an
original opening, and three rows corrected on the next run.

**The real lesson is that prose scanning is unreliable in both directions**, and
the durable fix is not a longer keyword list. The researcher should state the
event in **its own column** in the evidence CSV; until the schema carries that
field, the guard stops the commonest misfire and the residue is ruled one row at
a time.

**Why a table and not a rule.** The obvious fix — widen the keyword list that
already catches `replacement building` / `rebrand` / `relocat` — was tested and
**rejected**, because it makes the file worse. Thirteen researched rows mention
*expansion* or *replaced* in a note that is nonetheless dating the original
opening correctly: *"Describes the ORIGINAL casino opening, not the hotel/RV park
additions"* (The Mill Casino), *"not a later hotel or expansion"* (Muckleshoot).
A wider regex flips all thirteen to buy four. The four are ruled individually,
which is the same jurisprudence the project uses for per-UEI ownership drops.

### The 42 pre-IGRA facilities are correct — do not "clean" them

*(Count refreshed 2026-08-06: **52** pre-IGRA rows now, up from 42, as hand
research dated more of them. The argument is unchanged and so is the
instruction.)*

42 facilities carry an opening date before IGRA (1988). **Almost all are right,
and they are among the most substantively valuable rows in the dataset**: they
are the high-stakes bingo halls whose litigation produced IGRA in the first place.

| Year | Facilities |
|---|---|
| 1979 | **Seminole Classic Casino**, Hollywood FL — the *Butterworth* hall |
| 1981 | Seminole Casino Brighton · Big Bucks Bingo (Keweenaw Bay) · Indigo Sky (Eastern Shawnee) |
| 1982 | **Sycuan Casino** · Seminole Tampa · CRST Bingo |
| 1983 | **Casino Morongo** — *California v. Cabazon Band* era · Tachi Palace · Palace (Leech Lake) · Ada Gaming Center · Tulalip Bingo · Oneida IMAC |
| 1984–87 | 27 more, incl. Treasure Island, Cache Creek, Table Mountain, Fond-du-Luth, Mohawk Bingo Palace, Speaking Rock, Kings Club |

Only **3 of the 52** are anything other than a genuine pre-IGRA gaming opening,
and every one is named in `open_date_event`: Crosby Lodge (1905, verified
non-gaming), Singing Hills (1956, golf) and Pala Mesa (1961, golf). Seneca Irving
(1970) is unverified either way and says so. **Every other pre-IGRA row is a real
high-stakes bingo hall and belongs in the file** — including Yaamava'/San Manuel
(1986), whose own source says *"The 1986 date is the original facility opening,
not the Yaamava' rebrand or the hotel"*; it had been mislabelled `property_opened`
by a keyword misfire until 2026-08-06 (§2).

A future cleaning pass that filters "implausible pre-IGRA dates" would destroy
the origin story of the industry this dataset describes. **Do not.** The
filter you want is `open_date_event`, not the year.

### `open_date` is not a uniform ISO column, and the codebook used to say it was

Found 2026-08-06. Because the never-modify-the-source rule is applied strictly,
`open_date` holds three different shapes at once:

| shape | n |
|---|---:|
| `YYYY-MM-DD` | 506 |
| bare `YYYY` | 111 |
| literal `1980s` | 1 |

and `close_date` holds `YYYY-MM-DD` on 133 rows and a float artefact
(`2019.0`, `2005.0`) on 15. **The codebook declared the format as `YYYY-MM-DD`
for both.** A subscriber applying a strict ISO parser errors or silently drops
**112 opening dates and 15 closing dates** — and silently is the dangerous half,
because the resulting series looks complete.

Nothing was rewritten: the source value is the evidence, and the bare `YYYY`
rows are honestly year-precision. What changed is that the codebook now declares
the format as mixed and points at the fix — **`open_date_not_before` /
`open_date_not_after` are uniformly ISO with zero exceptions** (verified across
all 623 and 692 populated values, plus the close-date and `observed_open_by`
equivalents). They are also the better column to parse on the merits, since they
carry the interval the source supports instead of a padded point.

The general lesson for this project: **a codebook format string is a claim about
the data and needs measuring like any other.** These were declared from the
column's intent, not from its contents.

### Smaller defects, fixed the same way — without deleting anything

- **15 `close_date` values carry a float artefact** (`2019.0`, `2005.0`). Read as
  year precision; the literal value is retained.
- **One `open_date` reads `1980s`** (`CCP-750600` Lucky Star Casino – Watonga).
  A decade is a bound, not a date: classed `bounded`, interval
  `1980-01-01 … 1989-12-31`. The coverage audit's year regex would otherwise have
  read it as the year 1980 and asserted a precision the source never offered.

---

## 3. `date_basis` on every row

`open_date_class` is populated on all 774 facilities:

| class | meaning |
|---|---|
| `exact` | a source states the opening date, at the precision recorded |
| `bounded` | a source proves the facility was operating by a date, or could not have opened before one — but none states the opening |
| `absent` | no source located, or the row is not a datable facility |

Every `bounded` row carries at least one of `open_date_not_before` /
`open_date_not_after` plus `open_date_evidence` in plain words. Every `absent`
row carries `open_date_absent_reason`. **Nothing was dropped**; the 774 rows in
are the 774 rows out.

### Where bounds came from

**a. Observed operating in the capacity panel.** Where the Casino City panel
records a property with status `Open` on a date, the facility was operating by
that date. That is `open_date_not_after`, and it is not an opening date. Only
`observation_status = current` qualifies — `proposed` and `approved` are Casino
City's `Planned` and `Under Construction` rows, and a planned casino is not an
open one. This is the single largest bound source.

**b. BIA gaming-land decisions — one bound out of thirteen candidates.**
A land decision date bounds an opening from below only for the parcel it
decides, and a `(tribe, state)` join cannot establish that a facility sits on
that parcel. Thirteen undated facilities matched a decision on `(tribe, state)`.
**Twelve were rejected**, and the rejections are the more useful finding:

| Facility | Matched decision | Why rejected |
|---|---|---|
| Muckleshoot Casino Resort | `Muckleshoot Indian Tribe Decision`, 2008-12-12 | The casino has operated since the 1990s. The bound would have asserted it could not have opened before 2008. **Flatly wrong** — this one case is the whole argument against the automated join. |
| Pearl River Resort — Silver Star, Golden Moon | 2008-01-04, **Disapproved** | A disapproval takes no land into trust and bounds nothing. |
| Red Wind Casino | 2024-07-08, **Pending** | A pending application for a different project. |
| 4 further Cherokee Nation rows (Roland ×2, Will Rogers Downs, Hard Rock Tulsa) | 5 Cherokee decisions | 15 Cherokee facility rows against 5 decisions with no site key. Nothing links a decision to a facility. |
| Trade Winds Central Casino (Pawnee) | `Pawnee Nation of Oklahoma Decision`, 2019-10-07 | The title names no site; the tribe has 5 facility rows. |
| Prairie Flower Casino (Ponca NE row) | 2002-12-20 | A cross-reference stub for the Iowa property, not a distinct facility. |
| Cherokee Casino West Siloam Springs, West Siloam Springs Smoke Shop | `Cherokee Nation Siloam Spring Decision`, 1994-02-18 | The title *does* name their site — but it is an Oklahoma within-former-reservation-boundaries **gaming-eligibility determination**, not a land acquisition, and a Class II bingo operation could lawfully have preceded it on the same ground. A bound a bingo hall would falsify is not a bound. |

**Accepted: one.** `VP-0401` The Mill Casino, Coquille Indian Tribe — BIA decision
`GLD-OR-coquille-indian-tribe-19940622`, titled *Coquille Indian Tribe North Bend
Waterfront Decision* (Approved). The Mill Casino is on the North Bend waterfront
parcel; that decision acquires that specific site, which the tribe therefore did
not hold before it. `open_date_not_before = 1994-06-22`, and the evidence string
says in as many words that a decision date is not an opening date and that the
lag between them is not claimed here.

**c. Hand research against primary sources.** See section 4.

### Rows that are not datable facilities

24 rows are retained but can never carry an opening date, and are marked so
nobody reads them as an undated casino:

- **20 `not a gaming facility`.** These come from the votingpatterns roster,
  which carries one row per *tribe* and uses `facility_name` to record that the
  tribe operates no casino — literally `No casino`, `Pueblo of Jemez - no
  casino`, `Grand Canyon West - no casino`, `Tribal admin only - no casino`.
  There is no opening to date.
- **4 `cross-reference stub`.** `facility_name` points at another row for the
  same property — `Gold Country Casino & Hotel - see Mooretown`, `Dakota Magic
  Casino - actual ND`, `Prairie Flower Casino - actual IA`, `Yuma Quechan-side -
  see CA entry`. Not distinct facilities.

Note the trap avoided: several **travel plazas and smoke shops do host gaming**
(`Choctaw Travel Plaza Casino Too`, `Wewoka Trading Post Casino`,
`Watonga Bingo and Smoke Shop`). A name-based "not a casino" rule that keyed on
`travel plaza` or `smoke shop` would have thrown them out. Only the explicit
"no casino" wording was used.

---

## 4. Hand research — primary sources

### 4.1 The 2026-08-05 sweep — 93 facilities

Evidence file: `data/raw/external/gaming/facility_opening_research_2026-08-05.csv`.
One row per facility researched, carrying `source_url`, a **verbatim**
`source_quote`, and a `note` recording what the source does and does not
establish. The script reads it; nothing is typed into the clean file by hand.

| | exact | bounded | total |
|---|---:|---:|---:|
| California | 11 | 12 | 23 |
| West | 21 | 6 | 27 |
| Plains | 12 | 12 | 24 |
| Other | 15 | 4 | 19 |
| **Total** | **59** | **34** | **93** |

Exact dates span **1956–2022**. Their precision is recorded as the source states
it, never upgraded: **28 day · 10 month · 21 year**. A source that says *"opened
in 1996"* produces a year-precision row, not a 1 January.

Of the 34 bounds, **29 are "operating by" (upper) bounds**, 2 are lower bounds
and 3 have both ends.

**Where the evidence came from.** Counting by source domain:

| Source | n |
|---|---:|
| `web.archive.org` (Wayback) | 59 |
| Press, newswire, one court opinion | 15 |
| The property's, tribe's or operator's own live site | 14 |
| `sec.gov` (EDGAR) | 5 |

**Wayback supplied 63% of it**, which is the finding worth carrying forward.
Small tribal casinos routinely have no live page, no press coverage and no
anniversary release — but they had a website in 2003, and the archive kept it.
An archived capture of a casino's own site advertising its hours is not an
opening date and was never recorded as one; it is proof the property was
operating on the capture date, which is a genuine upper bound and the single
largest bound source in the sweep. This is `docs/ACCESS_TECHNIQUES.md` §1 working
exactly as advertised.

**EDGAR is the underrated one.** Five dates come from SEC filings, and they are
the *hardest* dates in the file to get any other way — Pearl River Silver Star
(1994-07) and Golden Moon (2002-08-26) from a Mississippi Choctaw bond filing,
Seneca Niagara (2002-12-31) and Seneca Allegany (2004-05-01) from Seneca Gaming
Corporation's 10-K, Mohegan Pennsylvania (2006-11-14) from the Mohegan Tribal
Gaming Authority's. See the Seneca Irving note in §2 for why this route exists at
all: a tribal gaming enterprise that issued public debt is an SEC registrant, and
its filings narrate the tribe's other gaming operations too.

### 4.2 The 2026-08-06 sweep

Evidence file: `data/raw/external/gaming/facility_opening_research_2026-08-06.csv`.

Most of this session's gain came from *applying* the 08-05 evidence that had
never been built in (75 of 93 rows — see the header), not from new research. The
new sweep targeted the Oklahoma worklist that the killed run had enumerated and
never worked.

**34 rows researched across three batches, 31 accepted, 3 rejected** — 18 exact
(5 day · 4 month · 9 year) and 13 bounded. Two of the three rejections are
**held dates**, not bad ones (§7.5c).

The rejection is the part worth keeping. `VP-0150` Indigo Sky was submitted as
`exact 2012-09` on the quote *"The Indigo Sky Casino held a soft opening in
September."* The validator refuses an `exact` row whose quote contains **no
digit**, because a quote that supports a stated date must contain the date. Here
the year came from the *article's publication date* (Indianz, 2012-11-09), which
is sound reasoning but is reasoning, not quotation. Rejected rather than
weakened. It is recoverable with a better quote.

**Retrieval conditions were unusual and are worth recording.**
`web.archive.org` was **down for most of the session** — `archive.org` answered
in 0.29s while `web.archive.org` timed out at 20s, so it was that subdomain and
not our network (see §7.4 and `docs/ACCESS_TECHNIQUES.md`). It recovered late.
The session's **WebSearch budget was also exhausted** (200/200) before the work
began. Wayback supplied 63% of the 08-05 evidence, so its loss removed the
principal method rather than merely slowing it. SEC EDGAR was unaffected and is
what produced the Seneca Irving result in §2.

### 4.3 The finding that matters more than the dates

**Researching the undated rows returned dates the file already held.**

| Row researched from scratch | Result | Already in the file |
|---|---|---|
| `VP-0185` Kiowa Casino Red River | **2007-05-23** | `CCP-773800` Kiowa Casino & Hotel — **2007-05-23** |
| `VP-0134` Cherokee Casino West Siloam Springs | 1994 | `CCP-408300` Cherokee Casino & Hotel West Siloam Springs — 1994-12-31 |
| `VP-0170` 7 Clans First Council Casino | 2008-03 | `CCP-843900` 7 Clans First Council Casino Hotel — 2008-02-29 |

Two independent routes producing the **same day** for `VP-0185` is not a
coincidence — it is duplication. See §7.5, which is the real story of the 56.

---

## 5. Coverage against 2000–2026

### Before and after

| | before | after |
|---|---|---|
| `gaming_facilities` | *no usable date column* | **1905–2025**, `open_date` |
| `gaming_facility_metrics` | *no usable date column* | **1994–2026**, `as_of_date`, **zero undated rows** |
| `gaming_decision_events` | not audited | 1990–2026 |
| `gaming_project_facilities` | not audited | 2013–2026 |
| `gaming_projections` | not audited | 2023–2026 |
| `gaming_mitigation_agreements` | not audited | 1992–2024 |

Gaming was the only dataset the audit could not place in time. It is now the
**only dataset in the project with a fully dated measurement file** — 65,223 of
65,223 rows, no interior gap anywhere in 1994–2026.

### The facilities file, graded

*Measured 2026-08-06, after the second research sweep.*

| | n | share |
|---|---:|---:|
| **exact** — a source states the opening date | 635 | 82% |
| **bounded** — proved to be operating by a date, or not before one | 90 | 12% |
| **absent** — no source located | 23 | 3% |
| **absent** — not a datable facility (20 non-casino rows + 4 stubs + **2 ruled**) | 26 | 3% |
| **at least some temporal evidence** | **725** | **94%** |

Movement across the two sweeps, on an unchanged 774 rows:

| | 2026-08-05 | 2026-08-06 |
|---|---:|---:|
| exact | 558 | **635** |
| bounded | 44 | **90** |
| absent, no source located | 148 | **23** |
| absent, not a datable facility | 24 | **26** |
| **some temporal evidence** | 602 (78%) | **725 (94%)** |

- Exact dates span **1905–2025**; **348 fall inside 2000–2026** and 287 before
  2000 (retained, per the flag-never-delete rule — a 1983 opening is not less
  reliable than a 2007 one).
- Bounded rows are pinned to intervals spanning **1980–2018** — that is
  `min(open_date_not_before)` to `max(open_date_not_after)`, the earliest and
  latest an opening could be across the bounded set, which is what the audit
  reports. **75 of the 90** carry an endpoint inside 2000–2026. None of it shows
  in the `open_date` range, which is why the audit reports the classes
  separately.
- The bounds are lopsided by construction: **87 of 90 carry an "operating by"
  upper bound and only 9 a lower bound.** That is the shape of the evidence, not
  a gap — proving a casino was *already open* on some date is easy (an archived
  page, a capacity observation), while proving it could *not* have opened before
  a date needs a land or licensing action tied to that specific site, which the
  land-decision analysis in §3 ("Where bounds came from") shows is rarely
  establishable.
- **Nothing was dropped.** 774 rows in, 774 rows out, across both sweeps.

### The measurement file

`as_of_date` on **65,223 of 65,223** rows, **1994–2026**, no interior gaps.
**99.9%** fall inside the 2000–2026 target window (the 36 outside are 1994–1999
revenue observations).

### Distance to the window

`gaming_facilities` now ends **2022**, four years short — raised from 2018 by
hand research on 2026-08-06.

**The 2018 ceiling belonged to the inherited column, not to the dataset**, and
that distinction is the point. `SOURCE_CEILINGS` now records **two ceilings**:
the Casino City `Open Date` column still stops in 2018, and everything after it
was dated by hand against primary sources. So post-2018 coverage is exactly as
complete as the hand research is and no more — a weaker guarantee than the
vendor-column years carry, and one a subscriber should be told about rather than
left to infer from a continuous-looking series.

**Openings after the last dated year are real and unsourced, not absent.** That
remains the honest statement; only the year moved.

---

## 6. Audit changes

`code/35_coverage_audit.py`:

1. **`DATE_COLS`** gains `open_date`, `as_of_date`, `observation_date`,
   `observation_period`, `document_date`, `source_document_date` — appended, so
   no existing dataset's column choice changes. A comment records why: an entity
   dataset dates itself with a lifespan column and a measurement dataset with an
   as-of column, and neither looks like a transaction's `action_date`.
2. **`DATASETS`** — the glob `gaming_facilit*.csv` is replaced by explicit
   entries. It had pooled the facility file and the metrics file into one
   dataset, which would have put a 2019 slot count in the same series as a 1987
   opening. Four further gaming files that were never audited at all are now
   registered: `gaming_decision_events`, `gaming_project_facilities`,
   `gaming_projections`, `gaming_mitigation_agreements`.
3. **`EVENT_DATASETS`** gains the gaming files. Openings are events: there is no
   defect in a year with no tribal casino opening, and without this the audit
   would have reported the 1906–1969 stretch as 64 interior gaps.
4. **`SOURCE_CEILINGS`** is new — the mirror of `SOURCE_FLOORS`. A dataset can be
   complete and still stop short of the present because its source does, and
   before this the audit had no way to say so. Undocumented ceilings still
   report as unfinished work.
5. **`CLASS_COLS`** is new — a dataset that grades its own date evidence gets an
   `Undated is not one thing` section separating **bounded** from **absent**.
   Pooling them understates the dataset, because a bounded row can be filtered,
   ranked and placed in an interval and a missing one cannot.

---

## 7. What could not be dated, and what was tried

**23 facilities carry `open_date_class = absent` with reason `no source
located`** after all sweeps (56 after the first). **Read §7.5 before treating
this as a research backlog — most of it is duplicate rows.** They are retained in full — 774 rows in, 774 rows out — and they
split into two groups that deserve very different treatment, because *one group
was searched and one group never was*.

### 7.1 The reconciliation

The 2026-08-05 sweep worked from five regional worklists. Reconciling those
against the evidence file accounts for every one of the 56 that stood after the
first sweep, with nothing left over:

| Worklist | Enumerated | Dated | Not found |
|---|---:|---:|---:|
| `research_A_OK` | 33 | **0** → 21 on 2026-08-06 | **33** → **12** |
| `research_B_CA` | 27 | 23 | 4 |
| `research_C_WEST` | 33 | 27 | 6 |
| `research_D_PLAINS` | 35 | 24 | 11 |
| `research_E_OTHER` | 21 | 19 | 2 |
| **Total** | **149** | **93** → **124** | **56** → **23** |

Every absent facility appears in exactly one worklist; none is unaccounted for.

**The Oklahoma worklist has a hit rate of zero because it was never run.** The
2026-08-05 session was terminated by a spend limit after enumerating those 33
facilities and before researching any of them. That is a *known, bounded, and
cheap* gap, not a research failure — the 33 are large, well-documented casinos
(Osage, Muscogee, Cherokee, Choctaw, Kiowa, Sac and Fox) that publish their own
histories. **Do not read the Oklahoma zero as evidence these dates are hard to
get.**

The other **23** were genuinely searched and not found. Their hit rate across the
four worked regions was 93 of 116 (**80%**).

### 7.2 What was tried on the 23 that were searched

The method was the same for every one: an origin fetch of the property's and the
tribe's own site; a Wayback CDX enumeration of both domains (which is what dated
59 of the 93 successes); a press search; and, where a gaming enterprise had
public debt, SEC EDGAR.

The 23 that survived that are not a random sample. They cluster into recognisable
kinds, and the kind explains the failure:

| Facility | Tribe | State |
|---|---|---|
| Klawock IRA Smoke Shop | Klawock Cooperative Association | AK |
| Elem Indian Colony Casino | Elem Indian Colony | CA |
| Lazy K-Bar Casino (closed) | Manzanita Band of Kumeyaay Nation | CA |
| Mesa Grande Casino - small | Mesa Grande Band of Diegueno Mission Indians | CA |
| Pala Casino - hotel tower | Pala Band of Mission Indians | CA |
| Big Cypress Casino - small bingo | Seminole Tribe of Florida | FL |
| Casino White Cloud | Iowa Tribe of Kansas and Nebraska | KS |
| Leelanau Sands Casino | Grand Traverse Band of Ottawa and Chippewa | MI |
| MidJim #2 | Sault Ste. Marie Tribe of Chippewa Indians | MI |
| MidJim St. Ignace | Sault Ste. Marie Tribe of Chippewa Indians | MI |
| Northern Lights Casino Hotel | Leech Lake Band of Ojibwe | MN |
| 4 J's | Assiniboine and Sioux Tribes, Fort Peck | MT |
| 4C's Cafe & Casino | Fort Belknap Indian Community | MT |
| KC Lodge | Assiniboine and Sioux Tribes, Fort Peck | MT |
| Iron Horse Casino - small | Omaha Tribe of Nebraska | NE |
| WinneVegas-Lite (closed) | Winnebago Tribe of Nebraska | NE |
| Sage Hill Casino | Shoshone-Paiute Tribes | NV |
| Golden Buffalo Casino | Lower Brule Sioux Tribe | SD |
| Emerald Queen Casino Tacoma | Puyallup Tribe of Indians | WA |
| Emerald Queen Hotel & Casino I-5 | Puyallup Tribe of Indians | WA |
| Oneida Casino - Main | Oneida Nation of Wisconsin | WI |
| Oneida Casino - Mason Street | Oneida Nation of Wisconsin | WI |
| Sevenwinds Casino Lodge & Hotel | Lac Courte Oreilles Band | WI |

**Three failure modes, and only one of them is about the web.**

1. **The row is a size or component variant, not a property.** `Pala Casino -
   hotel tower`, `Mesa Grande Casino - small`, `Big Cypress Casino - small
   bingo`, `Iron Horse Casino - small`, `Oneida Casino - Main` / `- Mason
   Street`, `WinStar Casino - additional plaza`. These names come from the
   votingpatterns roster and describe a *part* of a property or a size class of
   it. There is often no distinct opening event to find, because there is no
   distinct property. **These need a ruling on what the row is before more
   searching is justified** — searching harder cannot fix a row whose subject is
   undefined.
2. **The row may not host gaming at all.** `MidJim` is the Sault Tribe's
   convenience-store and fuel brand; `Klawock IRA Smoke Shop`, `4 J's`, `KC
   Lodge` are similar. The build already refuses to key "not a casino" off names
   like *travel plaza* or *smoke shop*, because several such properties
   demonstrably **do** host gaming (`Choctaw Travel Plaza Casino Too`, `Wewoka
   Trading Post Casino`, `Watonga Bingo and Smoke Shop`). So these stay as
   undated facilities rather than being reclassified on a guess. Confirming that
   any of them hosts no gaming would be worth more than a date.
3. **Small, rural, or long-closed, with no archived web presence.** `Lazy K-Bar
   Casino (closed)`, `Elem Indian Colony Casino`, `Sage Hill Casino`, `4C's Cafe
   & Casino`, `Golden Buffalo Casino`. A casino that closed before it had a
   website leaves very little. This is the only group where the honest summary is
   "the record may not exist."

A handful are none of the above and are simply unfinished — `Northern Lights
Casino Hotel`, `Leelanau Sands Casino`, `Casino White Cloud`, `Sevenwinds`,
`Emerald Queen` — substantial properties whose dates should be obtainable.
Emerald Queen in particular has a well-documented riverboat-to-land history.

### 7.3 The 24 that can never be dated, and should not be counted as failures

Separately from the 56: **20 rows are not gaming facilities** (votingpatterns
roster rows whose `facility_name` records that the tribe operates *no* casino —
literally `No casino`, `Pueblo of Jemez - no casino`) and **4 are
cross-reference stubs** pointing at another row for the same property. They
carry `open_date_absent_reason` saying so. Counting them among "undated casinos"
would overstate the gap by 24 rows.

### 7.4 What the 2026-08-06 session could not use

Two retrieval routes that produced most of the 08-05 evidence were unavailable:

- **`web.archive.org` was down for the entire session** — `archive.org` answered
  in 0.29s while `web.archive.org` timed out at 20s, so it was that subdomain
  and not our network or our IP. CDX returned `503 No server is available` before
  going dark. **This removed the single largest evidence source in the project**
  (59 of 93 rows on 08-05). No poller was left running; see
  `docs/ACCESS_TECHNIQUES.md`.
- **The session's WebSearch budget was exhausted** (200 of 200) before this work
  began.

Origin fetches and SEC EDGAR still worked, and EDGAR is what produced the Seneca
Irving result.

### 7.5 Most of the "undated facilities" are duplicate rows, not missing research

This reframes the whole undated count, and it was found by *trying* the research
rather than by reasoning about it.

**49 of the 56 undated rows carried `duplicate_risk = 1` already.** They are
`votingpatterns_only_no_exact_casino_city_match` rows — the roster contributes
one row per tribe-property under its own naming, and where it did not match a
Casino City row exactly, a **second row for the same property** entered the file.
Those second rows have no `open_date`, because Casino City's date is on the twin.

The 2026-08-06 sweep demonstrated it instead of asserting it: researching
`VP-0185` from primary sources returned **2007-05-23**, which is byte-identical
to the date already sitting on `CCP-773800` for the same casino in the same town
(§4.3). Three more matched their twin to the month or year.

**So researching these rows harder is the wrong move.** It produces a second
*dated* row for one property, and that double-counts in any openings-by-year
series — the exact failure the `open_date_postdates_observation` flag exists to
prevent, arriving through a different door. Undated, the duplicate was at least
invisible to a year series; dated, it is not.

`code/23g_gaming_duplicate_candidates.py` writes
`review/gaming_facility_duplicate_candidates_2026-08-06.csv`:

| | |
|---|---:|
| undated rows examined | 23 |
| candidate pairs emitted | 42 |
| **undated rows with a STRONG or likely twin** | **7 of 23** |
| undated rows with no candidate at all | 6 |

**It rules nothing and merges nothing.** It emits candidates with a blank
`YOUR_RULING` column, in the project's reconcile-queue format, because the
matching rules forbid the automated leap that is tempting here. The queue itself
demonstrates why:

- `VP-0202 Tonkawa Casino` matches **two** dated rows — `Tonkawa Gasino` (1999)
  and `Tonkawa Hotel & Casino` (2014). One tribe, one town, two properties or one
  rebuilt. A scorer cannot tell; a human reading the row can.
- `VP-0160 FireLake Express Grand` matches both `FireLake Casino` (1989) and
  `Grand Casino Hotel Resort` (2006) — its name contains tokens from each.
- A **property-type guard** was added after the first run scored
  `Choctaw Casino Atoka` identical to `Choctaw Travel Plaza - Atoka`. The
  stop-word list drops `casino`, `travel` and `plaza` so that
  "Kiowa Casino Red River" can reach "Kiowa Casino & Hotel" — and that same
  blurring made two genuinely different Atoka properties look like one. Pairs
  where exactly one side is a travel plaza, smoke shop, trading post or
  riverboat are now demoted, never merged away. **This matters because several
  tribal travel plazas really do host gaming**, so the file cannot treat
  "travel plaza" as "not a casino" in either direction.

**Recommended order of work**, which is the reverse of the obvious one: rule the
duplicate queue first, then research whatever is genuinely still undated.
Deduplicating first also shrinks the research list — and the 20.2% undated rate
is, to a substantial degree, a statement about row duplication rather than about
missing evidence.

### 7.5b Some rows do not describe a real, distinct property at all

The Oklahoma sweeps returned something more useful than dates: **ten of the
thirty-nine facilities they were asked to date turned out to have an identity
problem**, and no amount of searching would have produced a date because the
row's subject does not exist as described. These are in
`review/gaming_facility_identity_queue_2026-08-06.csv` (**17 rows**, blank
`YOUR_RULING`), and nothing was changed in `data/clean/` on the strength of them.

| Row | Problem |
|---|---|
| `VP-0169` **7 Clans Ponca Casino** | **Probable phantom.** *7 Clans* is the **Otoe-Missouria** brand (First Council, Paradise, Perry, Chilocco, Red Rock — no Ponca City property); the casino in Ponca City is the **Osage Nation's**; the Ponca Tribe's own casino is near **Enid**. The row appears to fuse an Otoe-Missouria brand, a Ponca tribe attribution and an Osage location. **That is a false attribution, which this project treats as worse than a gap.** |
| `VP-0155` **Peoria Ridge Resort** | **No gaming.** An 18-hole golf course; `peoriatribe.com` lists Buffalo Run Casino and Peoria Ridge *Golf Course* as separate enterprises. Same class as Lake of Isles (§2). |
| `TPL-0128` **Seminole Nation Travel Plaza** | Seminole Nation Casinos states it has **three** properties and no travel plaza. The I-40 casino sits beside a Conoco station, the likely origin of the phantom row. Probable duplicate of `TPL-0127`. |
| `VP-0160` **FireLake Express Grand** | **The name does not resolve.** The tribe has exactly two gaming properties (Grand Casino, FireLake Casino); *FireLake Express* is its **grocery** chain. The label looks like two enterprise names merged. The duplicate queue scores it STRONG against **both** dated rows — which is the tell. **No date was recorded**, deliberately. |
| `VP-0123` **Choctaw Casino Atoka** | "Atoka" appears **nowhere** in 31,054 rows of `choctawcasinos.com` archive history. The tribe's casino list includes **Stringtown, which is in Atoka County**. |
| `VP-0202` **Tonkawa Casino** | The tribe runs Tonkawa **West**, **East** and Native Lights. The name identifies none of them, and the duplicate queue scores it STRONG against two dated rows (1999 and 2014). |
| `VP-0142` **Muscogee Nation Casino Tulsa** | No such standalone property. The Nation's Tulsa casino is **River Spirit** (2009); the 1985 evidence is for *Creek Nation Tulsa Bingo* at the same 81st & Riverside address — the lineage River Spirit grew from. |
| `VP-0133` **WinStar "additional plaza"** | WinStar is **one** Thackerville complex whose themed plazas (Beijing, Madrid, Paris, Rome…) were added across successive expansions. There is no "additional plaza" with an opening of its own. |
| `VP-0204` / `VP-0205` **Emerald Queen** | **City and name disagree.** The file has "Emerald Queen Casino **Tacoma**" located in **Fife**, and "Emerald Queen Hotel & Casino **I-5**" located in **Tacoma**. The operator has exactly two properties, one in each town. Research keyed on the *city* field; if the names are authoritative the two rows should be swapped. |
| `VP-0165` **Sac and Fox Casino Shawnee** | Researched under a superseded name — the property is now **Black Hawk Casino**. **Matching trap worth keeping: `sacandfoxcasino.com` belongs to a DIFFERENT TRIBE**, the Sac and Fox Nation of *Missouri* in Powhattan, Kansas. |

**The pattern is the same one §7.2 predicted from the outside and this confirms
from the inside**: the votingpatterns roster contributes one row per
*tribe-property* under its own naming, and where that naming is a brand, a
county, a merged label or an amenity, the row does not correspond 1:1 to a
casino. **Searching harder cannot date a row whose subject is undefined.**

Two further rows are dated but carry caveats worth ruling: `VP-0184` Kiowa
Hobart (2025-07-23 is the *Elk Creek* grand opening — if an earlier Hobart
casino existed, this dates the current building, and the file holds no capacity
observation to test it against) and `VP-0201` Fort Sill Apache, where the widely
repeated **January 1999** date traces **only to the 500 Nations directory** and
Wikipedia's uncited repetition of it. It was **not** recorded; the row is bounded
to "operating during 2000" from the casino's own archived page instead. That is
the never-falsely-attribute rule costing us a precise date on purpose.

### 7.5c Two true dates that were deliberately NOT recorded

The strongest illustration in this log of what "never falsely attribute" costs.
Both rows below have a **sourced, verbatim-quoted opening date**. Neither was
applied, and the merger rejects them by name with the reason attached.

**`VP-0393` Sage Hill Casino — wrong tribe, wrong state.** The row says
*Shoshone-Paiute Tribes, Owyhee, **Nevada***. Sage Hill Casino is on the **Fort
Hall Reservation near Blackfoot, Idaho**, and belongs to the
**Shoshone-Bannock** Tribes — the operator's own site places it *"3 mi South of
Blackfoot on Highway 91"*. A clean date exists (*"The tribe opened Sage Hill
Travel Center and Casino in February 2009"*). **Applying it would have dated a
Nevada row with an Idaho casino's opening**, and it would have looked
impeccable — verbatim quote, primary source, correct precision. The researcher
found no evidence the Shoshone-Paiute at Owyhee operate any casino at all, so
the row may itself be a phantom.

**`VP-0116` "Pala Casino - hotel tower" — not a distinct facility.** The
submitted date, 2001-04-03, is when gaming commenced at the *property*, and
`VP-0011` Pala Casino Spa Resort already carries it. Recording it again puts
**one opening on two rows** — the double-count §7.5 exists to prevent. The hotel
tower itself opened 2003-08-19, which is an expansion, not an opening.

**The general rule these two establish:** a date's quality is not the only
question. *Whose* date it is, and *what row* it lands on, are separate tests, and
a well-sourced date attached to a misidentified row is worse than no date —
because the citation makes it unfalsifiable by inspection.

### 7.5d Two rows retired as not gaming facilities

`TPL-0070` **MidJim #2** and `CCP-764800` **MidJim St. Ignace** are the Sault
Ste. Marie Tribe's **convenience-store and fuel brand**, listed separately from
Kewadin Casinos on the tribe's own enterprise menu:

> *"Midjim has two locations in the Upper Peninsula, in Sault Ste. Marie and St.
> Ignace. Both locations offer items such as gasoline, cigarettes, beer, wine and
> other convenience items."*

No mention of gaming, slots or a casino. Both moved from "undated casino" to
`not a gaming facility` — **but by an explicit per-row ruling in
`RULED_NOT_FACILITY`, never by a name rule.** §3 explains why that distinction is
load-bearing: this build deliberately refuses to key "not a casino" off
`travel plaza`, `smoke shop` or `trading post`, because Choctaw Travel Plaza
Casino Too, Wewoka Trading Post Casino and Watonga Bingo and Smoke Shop
demonstrably **do** host gaming. The only safe retirement is reading the
operator's own description, one row at a time.

A second defect on the same row: `CCP-764800` is labelled **St. Ignace** but
carries **2205 Shunk Road, which is in Sault Ste. Marie**. The two stores appear
to have been crossed. Queued, not corrected.

### 7.6b Researching an undated row found a defect on a DATED one

`VP-0261` Northern Lights Casino Hotel could not be dated — but establishing why
produced something better. The May 2001 date that circulates on tribal and local
sites describes *"the new facility, which opened in May of 2001"*: a **replacement
building**. The file's already-dated twin `CCP-67000` carries **2001-05-15**,
which is therefore very likely the rebuild rather than the original opening — and
`open_date_postdates_observation` cannot catch it, because there is no earlier
observation of the property.

**This is an argument for researching undated rows even when they turn out to be
duplicates.** The work does not only fill gaps; it audits the dates already
present. Queued rather than corrected, since the original opening could not be
sourced (the casino's earliest archived captures are register.com host
placeholders and the band's 2001 page is a 295-byte stub).

### 7.6 A conflation the duplicate queue exposed

`CCP-962300 Indigo Sky Casino & Resort` carries `1981-12-31`, and that row is one
of the 50 pre-IGRA facilities. But Indigo Sky (Eastern Shawnee, Wyandotte OK)
**opened in 2012**; the researcher's note records that it *replaced the tribe's
older Bordertown Casino*. So the 1981 date is almost certainly the predecessor
bingo operation's, carried on the successor's row — the same
property-versus-gaming conflation as §2, arriving through a *third* route:
a vendor carrying a lineage date on a rebuilt property.

Not corrected here: the 2012 evidence was rejected by the validator (§4.2) and
no source has been read that states the 1981 date's subject. **Flagged for
ruling**, and noted so that the pre-IGRA list in §2 is not read as 50 verified
pre-IGRA halls.

### 7.7 What to do next

1. **Rule the duplicate queue** (§7.5). Highest value, needs no network.
2. **The 33 Oklahoma facilities** should be re-attempted with Wayback available
   — but *after* deduplication, since several will dissolve into existing rows.
3. Re-quote `VP-0150` Indigo Sky so the 2012 date can pass the validator, and
   resolve the 1981 conflation in §7.6.

### 7.8 How to absorb research that arrives later

The Oklahoma batches (A and B) landed late and **were absorbed** — batch A after
its first partial read, then again when it finished with 13 rows rather than 9,
and batch B with 15. That re-absorption cost nothing, which is the point of the
design below.

All three batches landed and were absorbed. The third returned only 6 dated rows
from 17 facilities, but **its non-dates were its most valuable output** — two
rows retired as convenience stores (§7.5d), two dates deliberately held
(§7.5c), and a defect found on an already-dated row (§7.6b).

Its author flagged a caveat that should be carried: **every general search engine
tried — DuckDuckGo, Yahoo, Bing, Brave, Startpage, Mojeek, Ecosia, Qwant, Yandex,
SearXNG — CAPTCHA'd or errored after a handful of queries**, on top of the
exhausted WebSearch budget. So the remaining not-founds mean *"not findable via
Wayback and direct site fetches"*, **not** *"searched exhaustively"*. The obscure
Montana, Nebraska and Alaska rows deserve a re-run with a working search tool
before anyone concludes the record does not exist. **Nothing is lost and nothing needs rewriting** — the pipeline was changed
on 2026-08-06 specifically so that late evidence drops in:

```
1. put the rows in data/raw/external/gaming/facility_opening_research_<date>.csv
   (validate first - the merger in the scratchpad rejects a row with no
   verbatim quote, no URL, a non-ISO date, or an `exact` row whose quote
   contains no digit)
2. py -3 code/23f_gaming_temporal.py     # globs every research_*.csv
3. py -3 code/23g_gaming_duplicate_candidates.py
4. py -3 code/35_coverage_audit.py       # then re-measure §5 from the audit
```

`code/23f` reads **every** `facility_opening_research_*.csv` in date order and
clears its derived columns on each run, so re-running is always safe and a later
sweep supersedes an earlier one on the same facility. **Do not append new
research to the 2026-08-05 file** — one file per sweep is what keeps the evidence
auditable.

**Curation happens at merge time, in code.** The scratchpad batch CSVs are raw
agent output and are left untouched; changes are made in the merger's
`OVERRIDES` table so they are reviewable and explained. One override was applied:
`VP-0205` Emerald Queen Tacoma was submitted `exact 2020-06-08` on a
**prospective** source ("will open June 8", published a week earlier) with the
researcher's own note recording *no post-hoc confirmation*. The 2026-08-05 sweep
had faced exactly this with the new Cahuilla Casino Hotel and recorded it
**bounded**; the same standard was applied here. **An announcement is evidence
the property was not yet open, not evidence of the day it opened** — and the
Cahuilla opening did in fact slip. Demoted to bounded (`2020-06-01 …
2026-08-06`), announced date preserved in the note.

**And do the deduplication first (§7.5).** Several of the facilities dated in
these batches — Osage Tulsa/Skiatook/Ponca City, the Muscogee properties,
Emerald Queen, Oneida, Sevenwinds — have a STRONG or likely dated twin in the
review queue. Dating them before ruling the duplicates is how the file ends up
with two dated rows for one casino, and some of that has now happened: the
undated pool fell from 56 to 29, but **9 of the remaining 29 still have a
STRONG twin** and several newly-dated rows sit opposite an already-dated one.

---

## 8. Open items for Elijah

1. **`*_date_basis` columns tier `internal`** under `code/41_build_codebooks.py`'s
   `_basis$` rule, which was written for columns that *are* the classifier
   recipe. `as_of_date_basis`, `open_date_basis` and `close_date_basis` are not
   recipes — they are the interpretive guidance a subscriber needs in order to
   read the date at all, and the same argument applies to `value_basis`, which
   `STATE_OF_BUILD.md` tells readers to consult before quoting any dollar figure
   while the codebook marks it internal. Not changed here; it is a policy call.
   **`open_date_event_basis` makes this acute**: `open_date_event` publishes
   (good) but the string explaining *why the date marks that event* — including
   the Crosby Lodge verification — is withheld from the subscriber who most
   needs it. The `_basis$` rule was written for classifier recipes; these are
   citations.
   *(2026-08-06: this got sharper. `open_date_event_basis` now carries the SEC
   S-4 quote that is the only hard evidence anywhere about the Seneca Irving
   hall, and the four `RULED_EVENT` rulings explaining why Lake of Isles is a
   golf course. All of it is `internal` and none of it publishes.)*
2. **Openings after the last dated year** are real and unsourced, not absent.
   Raised to 2022 on 2026-08-06 by hand research; the inherited `Open Date`
   column still stops at 2018. Recorded as **two** ceilings — see §5 — because
   post-2018 coverage rests on hand research rather than on a vendor column and
   carries a weaker guarantee.
3. The `01-01` opening dates (8 rows) are mildly over-represented (1.4% against
   ~0.3% expected) but nowhere near the 12-31 signal. Left at day precision and
   noted rather than downgraded on 8 rows of weak evidence.
4. **`Crosby Lodge`'s `tribe` value looks like a location attribution, not
   ownership.** It is a family business on the Pyramid Lake reservation, and the
   dataset records `Pyramid Lake Paiute Tribe`. If that is wrong it is a *false
   attribution*, which the project's central rule treats as worse than a gap.
   Queued for the reconcile queue on 2026-08-05 and still open.
5. **Six rows are size or component variants rather than properties** — `Pala
   Casino - hotel tower`, `Mesa Grande Casino - small`, `Big Cypress Casino -
   small bingo`, `Iron Horse Casino - small`, `Oneida Casino - Main` /
   `- Mason Street`. They are counted as undated casinos and probably should not
   be. A ruling on what these rows *are* is worth more than further searching,
   which cannot date a row whose subject is undefined.
6. **Whether an amenity golf course belongs in a gaming-facility file.** `Lake
   of Isles` (Foxwoods golf), `Pala Mesa Resort` and `Singing Hills Golf Resort`
   are all golf properties owned by gaming tribes. They are correctly dated and
   correctly evented now, but they inflate any facility count read as "casinos".

---

## 9. 2026-08-06, session 3 — the undated rows were duplicates, and the local sources already said so

*Appended, not rewritten. Everything above stands except where this section
withdraws it, and it withdraws three things.*

Two agents were killed by a spend limit before writing any output, so this
picks up from the file's state, not from their notes. Script changes are all
in `code/23f_gaming_temporal.py`; evidence in
`data/raw/external/gaming/facility_opening_research_2026-08-06_s3.csv`;
rulings ledger in
`review/gaming_facility_identity_rulings_2026-08-06_s3.csv`.

### 9.1 The counts

| | 2026-08-06 (before) | 2026-08-06 session 3 (after) |
|---|---:|---:|
| exact | 635 | **635** |
| bounded | 90 | **90** |
| absent | 49 | **49** |
| — of which **"no source located"** | **23** | **9** |
| — duplicate rows, date lives on a twin | 0 | **9** |
| — retired: not a gaming facility / not a distinct property | 0 | **3** |
| — identity not established | 0 | **2** |
| — gaming status not established | 0 | **2** |
| rows in / rows out | 774 / 774 | **774 / 774** |

**Not one new opening date, and the file is materially better.** The undated
pool fell by 61% without a single date being added, because §7.5 was right:
the rows were not missing research, they were duplicate and misidentified rows
wearing the same `absent` label as genuine gaps. `duplicate_of_facility_id` is
a new column carrying the twin.

`code/23g` re-run afterwards reports **0 of the remaining 9 undated rows have a
STRONG or likely twin**, down from 7 of 23. The duplicate queue is drained.

### 9.2 The method that worked, and it was not the web

`web.archive.org` and `archive.org` both timed out at 20s while the
`archive.org/wayback/available` API answered over plain HTTP in 1.8s, and the
WebSearch budget was exhausted at **200/200 before work began** — the *same two
conditions* §7.4 and §7.8 recorded, now on their third consecutive session.
Live-site fetches worked and produced two results. Everything else came from
**three files already in this repository**:

| Local source | What it settled |
|---|---|
| `directory_core/canonical_casino_addresses_supplement.csv` | The votingpatterns roster every `VP-*` row is built from. It carries a per-record **`notes`** column, and on several undated rows that column says **in as many words** that the row is not a distinct property: *"Same property"* (Pala hotel tower), *"Same property as primary"* (WinStar additional plaza), *"Main casino in IA"* (WinneVegas-Lite), *"Adjacent to Grand"* (FireLake Express Grand). It also carries a **`source`** column recording which website each row was built from. |
| `directory_core/Indian Gaming Dataset.xlsx` | Per-event opening/closing history with a source URL and a "last reviewed" date on every event. Supplied the Indigo Sky 2012 grand opening, the Bordertown 2005/2013 lifespan, the Two Rivers Casino 2010–2013 record that dissolved the 7 Clans Ponca row, and address-level confirmation on three duplicates. |
| `directory_core/Tribal Property List.xlsx` | Casino City's raw roster, with the close dates that overturned two prior rulings (§9.5). |

**The duplication was disclosed at source and had simply never been read.** The
lesson generalises beyond gaming and is the one worth carrying: *before
researching a gap, read the columns the source shipped alongside the value.*
The `notes` and `source` fields cost nothing to consult and settled six rows
that a full Wayback sweep had failed to settle across two earlier sessions.

### 9.3 Nine duplicate rulings

Each is in `RULED_DUPLICATE` in `code/23f` with its evidence, and **none copies
the twin's date across** — that would put one opening on two rows, the
double-count §7.5 exists to prevent. The row is retained; the reason names the
twin; `duplicate_of_facility_id` points at it.

| Row | Twin (carries the date) | What settled it |
|---|---|---|
| `VP-0116` Pala Casino - hotel tower | `VP-0011` (2001-04-03) | Roster note *"Same property"*; address 11154 Hwy 76 byte-identical |
| `VP-0133` WinStar - additional plaza | `CCP-411600` (2003) | Roster note *"Same property as primary"*; 777 Casino Ave is WinStar's own address in the Indian Gaming Dataset |
| `VP-0261` Northern Lights Casino Hotel | `CCP-67000` (2001-05-15) | Byte-identical address; roster cites the twin's own site |
| `VP-0371` Golden Buffalo Casino | `CCP-11800` (1992-02-15) | Byte-identical address; IGD records a 1992 grand opening at it |
| `VP-0393` Sage Hill Casino | `CCP-908000` (2009-03-18) | **Wrong tribe and wrong state** — see below |
| `VP-0362` WinneVegas-Lite - main IA | `CCP-39900` (1992) | Roster note *"Main casino in IA"*; cross-reference stub |
| `VP-0363` Iron Horse Casino - small | `CCP-688700` (2004-07-09) | Roster cites the twin's own site; **tribe on the row is wrong** |
| `VP-0164` Sac and Fox Casino Stroud | `CCP-800600` (2005-06-15) | Same 356120 house number as IGD's Stroud casino |
| `VP-0150` Indigo Sky Casino | `CCP-962300` (1981-12-31) | Same property — and **this row holds the correct address** |

#### Sage Hill — the §7.5c date was held for exactly the right reason

§7.5c held a clean, verbatim-quoted opening date off `VP-0393` because the row
said *Shoshone-Paiute Tribes, Owyhee, **Nevada*** and the casino is
Shoshone-Bannock, at Fort Hall, **Idaho**. This session found the rest of it:
**the file already holds the property correctly**, as `CCP-908000 Sage Hill
Casino, Shoshone-Bannock Tribes, Idaho, 2009-03-18`. So the held date was not
merely attached to a mislabelled row — it would have created a *second dated
row* for a casino this dataset had right all along. The roster's own `source`
column names `SageHillCasino.com` and its `notes` column says `NV side`: it
knowingly filed an Idaho casino under a Nevada tribe.

**And this is a defect in `code/23g`, not only in the data.** The duplicate
scorer searches for candidates *within a state*, so it could never find this
twin — the field it searches on is the corrupted one. A scorer that keys on the
field most likely to be wrong is blind to precisely the worst rows. Recorded
rather than fixed, because widening 23g to a national search would flood the
queue; the honest fix is a name-first pass over rows whose tribe or state is
independently doubted.

*Unresolved and queued:* the held source says **February 2009** and Casino City
says **2009-03-18**. Both are early 2009. Neither is preferred here. It is
worth noting that February may date the *travel center* and March the *casino*,
which would be the same property-versus-gaming distinction §2 turns on.

### 9.4 Three rows retired, and one date deliberately not recorded

`VP-0155` **Peoria Ridge Resort** — the Peoria Tribe's 18-hole golf course, the
same class of row as Lake of Isles (§2). Its address is the course; the tribe's
casino is `CCP-646400` at a different address. **The duplicate scorer rated it
`STRONG` against that casino on name tokens alone**, which is the cleanest
demonstration in this file of why 23g emits candidates and never merges.

`VP-0169` **7 Clans Ponca Casino** — the three-nation collision, now closed.
Every property the row could denote is already in the file and dated: the Ponca
Tribe of Oklahoma's Ponca City casino is `CCP-411000 Blue Star Gaming and
Casino, 20 White Eagle Drive, 2010-10-15`, which the Indian Gaming Dataset
independently records at the same White Eagle site as *Two Rivers Casino*,
grand opening 2010, **closed 2013**; the Osage Nation's is `CCP-859600` /
`VP-0199` (2007); and all six `7 Clans` rows in this file are Otoe-Missouria.

`VP-0160` **FireLake Express Grand** — the roster's own note reads *"Adjacent
to Grand"* and cites `GrandResortOK.com`, so the source recorded an adjunct of
the Grand Casino, not a casino. An **October 2006 date was available for the
Grand and was deliberately not recorded**, for the same reason as §7.5c.

### 9.5 Three prior rulings withdrawn — a 2026 web page cannot refute a 2003 record

This is the finding that most deserves to outlive the rows it is about.

**`TPL-0070` MidJim #2 and `CCP-764800` MidJim St. Ignace** were retired on
2026-08-06 as `not a gaming facility`, ruled against saulttribe.com's **current**
enterprise page describing MidJim as a convenience-store and fuel brand. But
both rows are **Casino City Tribal Property List records carrying close dates —
2003-11-21 and 2005-03-15**. The page describes a brand in 2026; the rows
describe locations that stopped operating twenty years earlier. The evidence
and the claim are not about the same thing.

Worse, the vendor list is a **gaming** roster, and its Montana section proves
it: it carries `B & S Laundry`, `Dad's Bar`, `TJ's Quikstop` and `Allard's
General Store`, which are licensed video-gambling locations, not casinos. **A
tribal convenience store appearing in that roster is evidence *for* gaming at
the location, not against it** — which is the same point §3 makes when it
refuses to key "not a casino" off `travel plaza` or `smoke shop`. The
retirement asserted a negative its evidence could not carry, exactly as the
`not_gaming_commencement` rule did before §2 corrected it.

Both rows move to `RULED_GAMING_UNCERTAIN`: still `absent`, still out of the
"undated casino" pool, but the reason now **states both sides and rules
neither**.

**`TPL-0128` Seminole Nation Travel Plaza** was queued on 2026-08-06 as a
*probable phantom*, because seminolenationcasinos.com states the Nation has
three properties and no travel plaza. Same defect: that is a statement about
2026. Casino City carries this row with a close date of **2003-06-14 — the same
day it closes `I 40 Seminole Casino`, `Konawa Rivermist Casino`, `Seminole
Nation Bingo & Casino` and `Wewoka Trading Post Casino`.** Five properties
closing on one date is a mass-closure event, not a data artefact. **The row is a
real property that closed.** It is not retired and not merged; it stays `no
source located` for its opening, which is the honest state.

The general rule these three establish, and it is a live risk everywhere in
this project: **when the evidence is a live web page and the row is a closed
record, check the dates before ruling.** A tribe's current enterprise menu is
excellent evidence about the tribe's current enterprises and no evidence at all
about a location the vendor closed in 2003.

### 9.6 Three corrections on rows that were already dated

`CCP-67000` **Northern Lights Casino** — §7.6b resolved. The 2001-05-15 date is
a **replacement building**: the circulating May 2001 statements describe *"the
new facility, which opened in May of 2001"*. Now `open_date_event =
property_opened`. The date is unchanged and the original opening remains
unsourced. Note *why* the automatic detector missed it: the file holds **no
earlier capacity observation** of the property, and
`open_date_postdates_observation` can only fire where one exists. A rebuild
date on a property with no observation history is in the detector's blind spot
by construction, and the only thing that reaches it is researching the undated
twin.

`CCP-962300` **Indigo Sky Casino & Resort** — §7.6 resolved. The stated
`1981-12-31` **cannot** mark Indigo Sky's opening. The Indian Gaming Dataset
dates Indigo Sky (70220 US-60) to a **2012 grand opening**, and this row's
Casino City address is **130 North Oneida Street** — which is the *predecessor*
Bordertown Casino's address (IGD puts Bordertown Casino & Arena at 129 Oneida
St, 2005 open, 2013 close). So the row carries a successor's name over a
predecessor's address with a date earlier than either: **a vendor carrying a
lineage date on a rebuilt property**, a third route to the property-versus-
gaming conflation of §2. The date is retained unmodified because no source read
here states what 1981 marks; the event basis now says all of this.
**Consequence for §2: this row must not be counted among the verified pre-IGRA
halls.** The pre-IGRA list's "only 3 of the 52 are anything other than a genuine
pre-IGRA gaming opening" should now read **4**.

*(The 2012 date itself is still not recorded on any row. The Indian Gaming
Dataset supplies the year and a source URL but not a verbatim quote containing
the date, and the validator rightly refuses an `exact` row on that basis — the
same refusal §4.2 documents. It is recoverable with a quote from the cited KOAM
report.)*

`CCP-336100` **Casino White Cloud** — no change of substance, but a **regression
closed**. The `permanent_facility_opened` ruling and `interim_open_date =
1998-05-20` had been applied **directly to the CSV**. `code/23f` clears
`open_date_event` on every row before recomputing it, so the next rebuild would
have silently reverted the row to `unspecified` and the interim-facility
distinction would have become an orphaned column with nothing pointing at it.
The ruling is now in `RULED_EVENT`, verified surviving two consecutive
rebuilds. **Any ruling applied to `data/clean/` by hand rather than to the
script that writes it is a ruling with a rebuild-shaped expiry date.**

### 9.7 The keyword guard, re-checked and now instrumented

§2 warns the rebuild keyword rule misfires in **both** directions. `code/23f`
now prints its behaviour on every run:

```
GUARD rebuild-keyword flips to property_opened   : 2
GUARD negation guard suppressed a flip           : 3
```

Three researcher *disclaimers* are still being correctly read as disclaimers
rather than claims, and two genuine rebuild disclosures still flip. Unchanged
by this session's edits. The counts are printed so that a future edit to either
keyword list shows up as a diff instead of as a silent re-labelling of correct
gaming-commencement dates.

### 9.8 Still open

In `review/gaming_facility_identity_rulings_2026-08-06_s3.csv` (33 rows, blank
`YOUR_RULING`).

1. **`VP-0170` 7 Clans First Council Casino is attributed to the wrong tribe**,
   and it is a **dated, publishing row** — found while retiring `VP-0169`.
   First Council is the Otoe-Missouria Tribe's, which the file's own
   `CCP-843900` says; the roster appears to have mis-attributed the 7 Clans
   brand to the Ponca Tribe systematically. Not changed here — the tribe and
   entity columns belong to another pipeline stage. **A false attribution is
   worse than a gap**, so this is the highest-priority open item.
2. **One date, two properties, two sources.** Casino City gives `CCP-692600`
   The Black Hawk Casino (Shawnee) an Open Date of `2004-07-28`; the Indian
   Gaming Dataset attaches an indianz.com article of that same date to the
   **Stroud** casino. One of them is dating the wrong building. Reading the
   article settles it.
3. **Sage Hill: February 2009 against 2009-03-18** (§9.3).
4. **`VP-0123` Choctaw Casino Atoka** and **`VP-0165` Sac and Fox Casino
   Shawnee** — both now `identity not established` rather than `no source
   located`, which is a more accurate description of the problem than either
   carried before. Neither was ruled a duplicate: `VP-0123`'s street number
   differs from the Atoka travel plaza's, and `VP-0165`'s name says Shawnee
   while its address is a Stroud address.
5. **`VP-0131` Sulphur Gaming Center** may be `CCP-1100100` The Artesian's
   predecessor. Casino City's *original* Open Date for The Artesian is
   `1998-12-31` (the file now carries 2010 from hand research), and the Indian
   Gaming Dataset carries four Artesian events. A Chickasaw gaming operation in
   Sulphur predating The Artesian is exactly what "Sulphur Gaming Center" would
   name.
6. **Nine rows are genuinely undated** — `CCP-41000` Klawock IRA Smoke Shop,
   `VP-0062` Lazy K-Bar, `VP-0067` Mesa Grande - small, `TPL-0088` 4 J's,
   `TPL-0090` KC Lodge, `VP-0385` 4C's Cafe & Casino, `TPL-0128` Seminole
   Nation Travel Plaza, `VP-0131` Sulphur Gaming Center, `VP-0168` Trade Winds
   Central Casino. Four are Montana or Alaska rows §7.2 grouped as *"may not
   host gaming at all"*; §9.5 shows that grouping was wrong for the Casino City
   ones. `VP-0067` is **not** ruled a duplicate because it is the Mesa Grande
   Band's only row in the file, so its `- small` suffix is a size descriptor
   with nothing to be a duplicate of.

**"Not found" still means "not findable via direct site fetches and local
sources", not "searched exhaustively"** — three consecutive sessions have now
run without Wayback and without a search budget. The nine are worth one more
pass with either restored, and not before.

---

## 10. 2026-08-06, session 4 — federal traces per property, and what a zero means

*Appended, not rewritten. Scripts: `code/88_gaming_property_federal_traces.py`,
`code/89_nigc_map_wayback_universe.py`, `code/92_stage_nigc_missing_properties.py`.
`data/clean/gaming_facilities.csv` was read and written zero times.*

Elijah, 2026-08-06:

> *"if we cant link them to federal actions in registra and compact they are
> probably quirky properties like a gas station or something."*

and, correcting the design mid-build:

> *"the class ii and iii are tricky cuz at any time a tribe can change their
> status by swapping out their machines so its a necessary but not sufficient
> condition."*

### 10.1 The correction is the finding

The first instinct — *no compact, therefore not a casino* — is wrong, and it is
wrong in a way that would have quietly deleted the most interesting properties
in the file.

**Class II gaming requires no tribal-state compact.** A bingo hall or card room
running Class II only will legitimately have no compact, no Class III Federal
Register approval, and no BIA gaming-land decision, and it is still a real
gaming operation. So "no compact" is evidence of *Class II or not-a-casino*,
never of *not-a-casino* alone.

**And gaming class is not a property attribute at all.** It is a time-varying
operational state. A tribe converts between Class II and Class III by changing
what is on the floor; Class II bingo-based machines and Class III slots look
alike to a visitor and can be swapped with **no federal record generated**.
Oklahoma tribes have run Class II fleets specifically to stay outside compact
revenue-sharing obligations. So:

- **No gaming class is assigned to any property.** `gaming_class_recorded`
  reads `NOT_RECORDED_BY_DESIGN` on all 774 rows.
- What is recorded instead is **dated observations with sources**:
  `compact_in_force_as_of`, `nigc_listed_as_of`, `land_decision_date`.
- **A compact is necessary-but-not-sufficient in BOTH directions.** Its
  *presence* does not prove Class III operation — a compact authorises, it does
  not observe. Its *absence* does not prove the property is not gaming. A
  compact trace may therefore only ever **raise** a count; it can never lower
  one and it can never on its own move a row toward `NOT_A_GAMING_PROPERTY`.

The enum carries no class value:
`CONFIRMED_GAMING | INSUFFICIENT_TRACE_REVIEW | NOT_A_GAMING_PROPERTY |
PLACEHOLDER_ROW | DUPLICATE`.

**This is also a further reason Cedar Press publishes no property-level
revenue.** Class II and Class III carry materially different revenue profiles,
the mix is unobservable per property, and it can change without notice. Anyone
modelling property GGR from machine counts is implicitly assuming a class mix
they cannot know. Staged as a comparability note in
`review/gaming_series_breaks_2026-08-06.csv` for the owner of
`data/clean/series_breaks.csv`, which was **not** edited.

### 10.2 A tribe-level trace cannot confirm a property, and the file proves it

This is the structural decision the whole build turns on.

A compact, a Federal Register Class III compact approval and a BIA gaming-land
decision are all keyed to a **tribe**. A tribe operating six casinos generates
one compact. Section 3 of this log already measured the cost of ignoring that:
of thirteen facilities matched to a BIA land decision on `(tribe, state)`,
**twelve were rejected**, including one whose bound would have asserted
Muckleshoot Casino could not have opened before 2008 when it had operated since
the 1990s.

So `federal_trace_count` counts **property-level traces only**. Tribe-level
traces get their own columns and their own count, are never summed in, and are
labelled on every row.

**The 16 placeholder rows are the test of that decision, and they pass.**

| | |
|---|---:|
| rows whose own `facility_name` denies a casino | 16 |
| scoring **zero** on `federal_trace_count` | **16** |
| **of those, carrying tribe-level federal traces** | **11** |

Las Vegas Paiute Smoke Shop and Pyramid Lake both carry a Federal Register
Class III compact approval **and** a compact index entry — because their tribes
do. Grand Canyon West, Pipe Spring, Ewiiaapaayp and the Yurok row are the same.
**Had compacts counted as property traces, a row that says `No casino` in its
own name would have scored two.** That is the whole argument for the split, and
it was available in the file the entire time.

### 10.3 The counts

| Trace | Attaches to | Fires on |
|---|---|---:|
| NIGC gaming location map | **property** | 350 |
| Federal Register Class III compact approval | tribe | 450 |
| Tribal-state compact index (BIA) | tribe | 672 |
| BIA gaming-land decision = IGRA sec. 20 determination | tribe | 268 |
| NIGC management contract approval | — | **0 at property grain — but the FAMILY is now held: `nigc_management_contract_approvals.csv`, 68 approvals / 55 tribes, promoted 2026-09-01. The trace stays 0 because the source is keyed to the TRIBE and joining it to a property would attribute a contract to a building on the strength of its owner. See 10.6.** |
| *(non-federal)* dated gaming-equipment observation | **property** | 429 |

| `federal_trace_count` (property-level) | rows |
|---|---:|
| 1 | 350 |
| 0 | 424 |

| `property_likelihood` | rows |
|---|---:|
| `CONFIRMED_GAMING` | 522 |
| `INSUFFICIENT_TRACE_REVIEW` | 214 |
| `PLACEHOLDER_ROW` | 16 |
| `DUPLICATE` | 15 |
| `NOT_A_GAMING_PROPERTY` | 7 |

38 rows carry `excluded_from_gaming_property_count = 1`. **Not one row was
deleted; 774 in, 774 out.** Exclusions are columns so a subscriber can
reproduce or disagree with our totals.

### 10.4 An IGRA sec. 20 determination and a BIA gaming-land decision are ONE record

The brief asked for these as two independent traces. They are not.

**BIA's Office of Indian Gaming index IS the section 20 index.** Every one of
its 138 rows carries a `legal_theory` that is a 25 U.S.C. 2719 exception —
Two-Part Secretarial Determination is 2719(b)(1)(A), Restored Lands is
2719(b)(1)(B)(iii), Initial Reservation 2719(b)(1)(B)(ii), Settlement of a Land
Claim 2719(b)(1)(B)(i), Within or Contiguous 2719(a)(1), Oklahoma Within Former
Reservation Boundaries 2719(a)(2)(A)(i).

Counting both would double-count a single federal action on every property of
138 tribes and inflate every triangulation score by one. One trace column
carries it, with the exception and its U.S. Code citation on the same record in
`igra_section20_exception` / `igra_section20_citation`.

### 10.5 What a zero does NOT mean — two measured false-zero mechanisms

`federal_trace_count = 0` on 424 rows. **It is not a claim that those properties
leave no federal trace**, and the file names both reasons it is not.

**(a) The NIGC roster match is deterministic and ONE-TO-ONE.** Nearest-first
greedy on coordinates within 1.2 km in the same state, then identical normalised
name in the same state. Where Cedar holds two rows for one property, only one
can claim the marker: `CCP-544900 Casino Del Sol` matched and its twin
`VP-0041 Casino Del Sol Resort` scored zero.

**(b) Real casinos miss outright.** `CCP-41700 Barona Resort & Casino` scored
**zero traces of any kind** — yet NIGC maps `Barona Valley Ranch Resort and
Casino` at 1932 Wildcat Canyon Road, Lakeside CA. The same property. The names
do not normalise equal and the coordinates did not come within 1.2 km.
`CCP-86600 Apache Gold Casino Resort` against NIGC's `Apache Gold Casino` is
the identical failure. **No name matcher was written to fix this** — that is
the containment defect's territory and AGENTS.md forbids it.

What was written instead is a **lead**, on a key that is exact string equality
on a parsed city and a state (NIGC prints `street, City ST ZIP`, so the city
comes out of the field's own shape — reading a structured field, not matching a
name). `nigc_unmatched_marker_in_same_city_state` fires on **116** rows. It is
excluded from every count and changes no classification.

The residue after both mechanisms: **26 rows carry no trace of any kind,
federal or vendor, at property or tribe level.** They are not junk. They are
the thesis:

| Row | Why it has no compact |
|---|---|
| `VP-0411` Naskila Casino (TX) | Alabama-Coushatta electronic bingo — **Class II, no compact exists or is required** |
| `CCP-69700` / `VP-0410` Speaking Rock (TX) | Ysleta del Sur — long-running Class II operation |
| `TPL-0139` Alabama-Coushatta Entertainment Center (TX) | same tribe, same posture |
| `CCP-43700` Mohawk Bingo Palace (NY) | a bingo hall |
| `CCP-41700` Barona, `VP-0013` Yaamava', `CCP-19700` Miccosukee, `CCP-21500` Oneida | **match failures per (b) — among the largest tribal casinos in the country** |

**A rule that deleted "no compact, no Federal Register" rows would have deleted
Naskila and Speaking Rock — Class II operations that are exactly what the
correction in 10.1 exists to protect — alongside Barona and Yaamava'.** The
zero is a review queue, not a verdict, and that is what
`INSUFFICIENT_TRACE_REVIEW` names.

### 10.6 NIGC management contract approvals — not held, and not asserted absent

> **CLOSED 2026-09-01, workstream INT-2.** The family was fetched by
> `code/344_pull_nigc_document_surface.py` and promoted by
> `code/586_promote_nigc_gaming.py` to
> **`data/clean/nigc_management_contract_approvals.csv` — 68 approvals across
> 55 tribes**, one row per Chair-approved management contract document, with
> the NIGC document URL, the retrieved PDF, its MD5 and a tribe key that
> `code/585_factcheck_nigc_keys.py` re-derived rather than inherited.
>
> Three things this section predicted, and how they turned out:
>
> - *"once that build lands, fill the trace from the declination letters
>   rather than a fresh pull"* — **that would have been wrong.** Declination
>   letters and management-contract approvals are two different NIGC document
>   categories (`declination-letters`, 329 documents; `approved-management-
>   contracts`, 68) and neither contains the other. The join would have
>   produced the wrong 68 rows. The pull was necessary.
> - *"absence under a filter is a property of the filter"* — held exactly.
>   Nobody had enumerated NIGC's document surface. It is **72 categories /
>   4,071 documents** and Cedar held five of the 72. The enumeration is now
>   itself a shipping table, `nigc_document_surface.csv`, 7,930
>   (category, document) memberships.
> - *the host-lock discipline that left this empty rather than half-fetched* —
>   correct then and still correct. One poller per host.
>
> **What is still open.** `trace_nigc_management_contract` on the 774 property
> rows is NOT filled by this promotion. The approvals table is keyed to the
> TRIBE, not to a facility, and NIGC's index names no property — so joining it
> onto a property row would be attributing a contract to a building on the
> strength of its owner. `gaming_facilities.csv` has a stated grain of 787
> rows / 786 facilities and one tribe routinely runs a dozen properties. The
> trace stays 0 and the honest join is tribe-level.

No retrieved NIGC management-contract file exists anywhere in `data/raw/`, and
this session did not add one. `trace_nigc_management_contract` is 0 on all 774
rows and `nigc_management_contract_status` reads
`not_held_by_cedar_press_this_session` — **recorded as NOT SEARCHED rather than
as absent**, because absence under a filter is a property of the filter. This
is the one trace the brief asked for that this build could not supply, and
saying so is more useful than a column of zeros that reads like evidence.

**A concurrent build is closing this gap and the two should be joined.**
While this session ran, another agent held the `www.nigc.gov` host lock
(`logs/_HOSTLOCK_www.nigc.gov.json`, `code/90_fetch_nigc_declinations.py`) and
wrote `data/clean/nigc_declination_letters.csv`. **A second poller against
nigc.gov was therefore not started** — one poller per host, per
`docs/PULL_DISCIPLINE.md` — which is why this trace is empty rather than
half-fetched. NIGC declination letters sit in the same statutory family as
management-contract approvals, so once that build lands,
`trace_nigc_management_contract` should be filled from it rather than from a
fresh pull. That is a join, not a fetch, and it costs nothing.

*(Numbering note: that agent also used `code/90`. This build's staging script
was renumbered to `code/92_stage_nigc_missing_properties.py` so the two do not
collide. `code/91` is likewise taken twice already.)*

### 10.7 Federal Register compact approvals — how the tribe was resolved

619 Federal Register documents are Class III compact actions. The tribe is named
**in the document itself** — either in the title (`Indian Gaming; Kaibab Band of
Paiute Indians, AZ`) or in the abstract (`has approved the Tribal-State Gaming
Compact Between the Narragansett Indian Tribe and the State of Rhode Island`).

| | |
|---|---:|
| compact documents scanned | 619 |
| a tribe name extractable from the text | 462 |
| **resolved to a spine entity** | **443** |
| refused as multi-tribe or boilerplate | 43 |
| named but unresolved — **held, not guessed** | 19 |

`resolve_entity` from `code/33_apply_party_rulings.py` did all the resolving.
**No new name matcher was written anywhere in this session.** Feeding it a tribe
string lifted verbatim out of a Federal Register notice is the sanctioned use of
the containment tier under AGENTS.md — *"containment may be used only to resolve
an owner already named in evidence, never to detect a match, and never to key a
dollar."* **No dollar is keyed anywhere in this build.**

The 43 refusals matter as much as the 443 successes. A notice covering *"three
Tribes in California"* or *"the following Tribe/Pueblos"* names no single tribe,
and resolving it to whichever tribe happened to match would be a false
attribution. Unresolved names are in
`review/gaming_fr_compact_unresolved_tribes_2026-08-06.csv`.

**A coverage limit worth stating:** 429 of the compact notices are titled bare
`Indian Gaming`, and 157 of the 619 name no tribe this script can extract. Those
tribes are named in the document *body*, which `federal_actions.csv` does not
carry. So `trace_fr_class_iii_compact_approval = 0` is a floor, not a census.

### 10.8 The 140 we are "missing" are mostly not missing — 125 of them

`review/gaming_additions_2026-08-06.csv`, 140 rows, `code/92`.

The roster diff's 140 `IN_NIGC_NOT_IN_CEDAR` rows were staged for addition by
the previous session. **They should not be added, and the same defect that
produces 10.5's false zeros is why.** A one-to-one match failure leaves the
*same property* looking absent at **both ends** of the diff — a Cedar row with
no NIGC marker, and an NIGC marker with no Cedar row.

| Disposition | Rows |
|---|---:|
| `PROBABLE_MATCH_FAILURE_DO_NOT_ADD` | **125** |
| `HOLD_UNRESOLVED` | 9 |
| `STAGE_FOR_ADDITION` | **6** |

The clearest pairs, each an NIGC "missing" property sitting in the same city and
state as a Cedar row that carries no marker of its own:

| NIGC marker | Cedar row it is probably the same as |
|---|---|
| Barona Valley Ranch Resort and Casino | `CCP-41700` Barona Resort & Casino |
| Apache Gold Casino | `CCP-86600` Apache Gold Casino Resort |
| Cliff Castle Casino | `CCP-65900` Cliff Castle Casino Hotel |
| Turning Stone Casino | `CCP-44400` Turning Stone Resort Casino |
| Seven Cedars Casino | `CCP-24850` 7 Cedars Casino |
| Prairie Knights Casino and Resort | `CCP-22700` Prairie Knights Casino & Resort |
| C.R.S.T. Bingo | `CCP-686200` CRST Bingo |
| Northwood Casino | `CCP-804800` Nooksack Northwood Casino |

**Six stage cleanly**, resolving to a spine entity with no Cedar row in their
city and state: Cherokee Casino West Siloam Springs (AR — note NIGC's own
Arkansas placement, already a recorded series break), Coyote Valley ShodaKai
Casino (CA), M&W Service of White Earth (MN), Flowing Waters Navajo Casino (NM),
Santa Ana Star Casino (NM), Seneca Entertainment Center Oil Springs (NY). Nine
are held unresolved. **Nothing was appended to `gaming_facilities.csv`.**

The general lesson, and it generalises past gaming: **a roster diff computed
with a one-to-one matcher double-counts every match failure — once as a false
`IN_SOURCE_NOT_IN_CEDAR` and once as a false `IN_CEDAR_NOT_IN_SOURCE`.** Both
halves of `docs/CROSS_SOURCE_VERIFICATION.md`'s three outcomes are inflated by
the same rows, and the inflation is invisible unless the two ends are joined
back together on a key the matcher did not use.

### 10.9 Wayback — the outcome, with probe evidence

`code/89_nigc_map_wayback_universe.py`, one poller,
`logs/_HOSTLOCK_web.archive.org.json` claimed before the first request,
sequential with a 5 s floor and exponential backoff to 900 s.

**web.archive.org is INTERMITTENT, not down — and that is a different diagnosis
from the one the last three sessions recorded.** Measured this session:

| Endpoint | Result |
|---|---|
| `http://archive.org/wayback/available?...` | **HTTP 429 Too Many Requests** in 0.19 s — the route 9.2 recommended is now rate-limited |
| `https://archive.org/wayback/available?...` | HTTP 429 in 0.28 s |
| `http://web.archive.org/cdx/search/cdx?...` | timeout at 20.0 s |
| `https://web.archive.org/web/2018/https://www.nigc.gov/map/` | **HTTP 200 in 2.02 s, 997,293 bytes** |
| the same URL, twenty minutes later | timeout at 45.0 s |

So the **`/web/<timestamp>/` redirect route is the one that answers**, and the
availability API that 9.2 found fast on 2026-08-06 is now the one that refuses.
Recommendation for the next session: **try `/web/` first, not the availability
API.** Full probe log at
`data/raw/external/nigc/locations/wayback/_probe_log_2026-08-06.csv`.

#### The retrieval finding worth carrying forward

The 2015-10-02 capture proves the historical universe is **fully recoverable
without replaying any AJAX call**. The pre-WordPress nigc.gov map embedded its
entire marker set as a hidden HTML table:

```html
<div id="locations" style="display:none">
  <tr>
    <td class="title">Thunderbird Casino - Shawnee</td>
    <td class="address">2051 S Gordon Cooper<br>Shawnee, OK 74801</td>
    <td class="region">Oklahoma City Region</td>
    <td class="lat">35.282570</td>
    <td class="lon">-96.930250</td>
```

**485 locations in the 2015 capture against 490 in the 2026 live pull** — and
the old table carries *more* than today's JSON does, since NIGC's own region
name is a column rather than an icon filename. The JavaScript read that table
to build the markers, so the table **is** the marker set.

This matters beyond this build: a Wayback capture of a JavaScript map is usually
assumed lost because the AJAX endpoint is not archived. Here it was never
needed. **Check for an embedded no-JS fallback before concluding a captured map
is unrecoverable.**

`extract_markers()` carries four routes and stamps `extract_route` on every
snapshot, so `extract_route_changed = 1` appears on every event in a diff
interval whose markup changed — otherwise a plugin migration reads as 490
properties all moving in one year. `--offline` rebuilds the whole universe from
saved HTML with no network at all, so improving the parser never costs another
request against a host that is already refusing.

#### The event vocabulary has no `closed` value

Per the standing rule, **disappearing from the NIGC map is not a closure.**
The vocabulary is `present_in_snapshot`, `absent_from_snapshot`,
`coordinates_changed`, `address_changed`. Every event carries both snapshot URLs
and both snapshot dates, and every `absent_from_snapshot` row carries a note
saying in as many words that it may be a delisting, a rename, a data refresh or
a submission gap, and that no closure is claimed without a document that says
closed.

#### Two requested event types the source cannot support, and why

The brief asked for six event types. Four are built:
`present_in_snapshot`, `absent_from_snapshot`, `renamed`, `coordinates_changed`
(plus `address_changed`). **Two are not, and they are not omitted for lack of
effort — the marker set carries no field that could produce them.**

- **`changed_operator`.** Neither vintage of the map has an operator field. The
  2026 JSON's `description` and the 2015 table's `td class="contact"` hold a
  *named individual and their job title* — `Judy Shutter, Casino Manager`. A
  general manager changing jobs is not a change of operator, and publishing it
  as one would be a fabricated event about a real person. Not built.
- **`temporary_replaced_by_permanent`.** This is a claim about two buildings and
  their relationship, and no marker attribute expresses it. It needs a document.
  `CCP-336100 Casino White Cloud` is already carried in the facility file with
  `interim_open_date` and a `permanent_facility_opened` ruling precisely because
  a *document* established it — that is the standard, and a map diff cannot meet
  it.

**Where a rename could not be paired, it is left as two events on purpose.**
`Fort McDowell Gaming Center` (2015, addressed *Fountain Hills AZ*) and
`Fort McDowell Casino` (2026, addressed *Fort McDowell AZ*) are one property,
but BOTH the name and the city changed, so no deterministic key pairs them.
Loosening the key to fuzzy name similarity is exactly the containment-defect
move AGENTS.md forbids. It publishes as `absent_from_snapshot` +
`present_in_snapshot`, and the absence note says in as many words that this is
not a closure. **An unpaired rename is a visible, correctable overcount; a
wrongly paired one is an invisible false statement about two properties.**

#### What the 2015-to-2026 interval actually contains

Ten events, every one checkable against the outside world:

| Event | Marker | What it really is |
|---|---|---|
| `renamed` | San Manuel Indian Bingo & Casino -> Yaamava' Resort & Casino at San Manuel | the 2021 rebrand, same building at 777 San Manuel Blvd |
| `renamed` | Kiowa Casino Verden -> Kiowa Casino Devol | same P.O. Box 100, Devol OK |
| `present_in_snapshot` | ilani Casino Hotel Resort | Cowlitz, opened 2017 — genuinely new |
| `present_in_snapshot` | Chukchansi Gold Resort and Casino | **absent in Oct 2015 because it was CLOSED** — NIGC ordered it shut in Oct 2014 and it reopened at the end of 2015. The map recorded the closure; this dataset records only that the marker was absent, which is the correct discipline even when a closure happens to be the true cause |
| `present_in_snapshot` x3 | Lakeside Entertainment II, III, IV | Cayuga Nation NY, post-2015 |
| `present_in_snapshot` / `absent_from_snapshot` | Fort McDowell Casino / Gaming Center | an unpaired rename, per above |
| `coordinates_changed` | Apache Gold Casino | a geocoding correction or a move; the map does not say which and neither does the row |

Chukchansi is the case that justifies the whole rule. Its absence from the 2015
map **was** caused by a closure — and the dataset still must not say so, because
the map is not what established that. The event says `absent_from_snapshot`, and
a subscriber who wants the closure can find the NIGC closure order. Had the
build been willing to infer closure from absence, it would have been right here
and wrong on the other 66 markers the first (buggy) run produced.

### 10.10 Files written

| Path | Rows |
|---|---:|
| `data/clean/gaming_property_federal_traces.csv` | 774 |
| `data/clean/gaming_property_universe_events.csv` | see 10.9 |
| `review/gaming_property_triage_2026-08-06.csv` | 774 |
| `review/gaming_additions_2026-08-06.csv` | 140 |
| `review/gaming_series_breaks_2026-08-06.csv` | 2 |
| `review/gaming_fr_compact_unresolved_tribes_2026-08-06.csv` | 14 |
| `data/raw/external/nigc/locations/wayback/` | captures + probe log |

**Not touched:** `data/clean/gaming_facilities.csv`, `series_breaks.csv`,
`nigc_*.csv`, `admin_region*.csv`. `code/01_build_entity_spine.py` was not run.
No property-level revenue exists anywhere in this build, and no dollar was read
from `gaming_facility_metrics.csv` — only its equipment-count metrics.

### 10.11 Still open

1. **Rule the 125 `PROBABLE_MATCH_FAILURE_DO_NOT_ADD` rows.** Highest value,
   needs no network, and it shrinks both ends of the roster diff at once.
   Barona and Apache Gold are one-line rulings.
2. **`CCP-41700` Barona and `VP-0013` Yaamava' carry no `tribe_id`**, so no
   tribe-level trace can reach them at all — 8 rows are in this state. That is
   an entity-keying gap, not evidence, and it belongs to another pipeline stage.
3. **NIGC management contract approvals** are the missing sixth trace (10.6).
4. **157 Federal Register compact notices name their tribe only in the document
   body** (10.7). Fetching bodies for those would raise the FR trace from a
   floor toward a census.
5. The 214 `INSUFFICIENT_TRACE_REVIEW` rows are the review queue Elijah's rule
   was asking for — but read 10.5 first: a substantial share are Class II halls
   and match failures, not gas stations.
