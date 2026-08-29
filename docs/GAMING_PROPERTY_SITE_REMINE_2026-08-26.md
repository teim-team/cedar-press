# Re-mining the property-site corpus — build log

*2026-08-26. Scripts `382`, `383`, `384`. Every number below is written by the
build to `logs/382_summary_2026-08-26.json`, `logs/383_summary_2026-08-26.json`
and `logs/384_summary_2026-08-26.json`; none is asserted by hand.*

---

## THE QUESTION

> *"Are you working on the casino gaming webscraping exercise, or downloading
> and reading or OCR'ing their marketing material to flesh out their data?"*

The honest answer on the morning of 2026-08-26 was **no**. 357 MB of operator
websites — 1,749 pages on 144 hosts — had been on disk since 2026-08-12 and had
produced **262 site observations, 43 labor-demand rows and 66 loyalty rows**.

`142_build_property_site_observations.py` mined that corpus for exactly one
thing: **capacity numbers, on ten metrics**. It never looked for the four other
kinds of fact a casino publishes about itself, and it refused 1,621 numbers
under a single reason it never revisited.

---

## PHASE 1 — RE-MINE WHAT WAS ALREADY DOWNLOADED

`code/382_remine_property_site_corpus.py`. **Zero network requests.**
1,739 pages read on 167 hosts.

| output (all staged) | rows | what it is |
|---|---:|---|
| `data/staging/gaming_property_self_published_claims_<date>.csv` | **41** | 29 employment + 12 capacity, typed measurements |
| `data/staging/gaming_property_self_published_assertions_<date>.csv` | **622** | 292 date · 169 ownership · 119 management · 46 employer-standing |
| `data/staging/gaming_property_loyalty_tiers_<date>.csv` | **65** | 22 programmes on 20 hosts, tier ladders |
| `review/gaming_property_claims_refused_382_<date>.csv` | 16 | refused, each with its own named reason |
| **total recovered** | **728** | from material that needed no network |

**Nothing was written to `data/clean/`.** `gaming_facility_metrics.csv` has
multiple writers and moved during the day; and creating a new clean table would
have moved five shipping counters `62` is already failing on for another agent.

### THE MEASUREMENT TYPES CREATED, AND WHY

Two new terms in `cedar_domain.MeasurementType`, written on the
`GAME_FINDER_OBSERVATION` pattern — a comment saying what one row IS and IS NOT:

| type | one row is | one row is NOT |
|---|---|---|
| `SELF_PUBLISHED_MARKETING_CLAIM` | a capacity figure the operator states about itself in marketing copy on its own site, on the date Cedar captured the page | an audited count |
| `SELF_PUBLISHED_EMPLOYMENT_CLAIM` | an employment figure the operator states about itself in marketing or about-us copy | a headcount of a declared population |

**Both are `is_observed`.** The operator did count its own floor and its own
payroll, on a real date. `is_observed` asserts that somebody counted a real
population — it does not assert the figure is exact, audited or current.

**Both are in `NEVER_PROMOTES_TO_ACTIVE`, and that is the load-bearing half.**
A regulator's count and a website's boast are different measurements of
different things. Marketing copy carries three defects a regulator filing does
not, and each is recorded per row rather than argued about in prose:

1. **Puffery.** "Over 1,500" is a floor, not a value. `value_is_bounded` and
   `bound_direction` (`LOWER_BOUND` / `UPPER_BOUND` / `APPROXIMATE` /
   `AS_STATED`) are read from the qualifier in the sentence itself.
2. **Rounding.** "2,000 slot machines" is almost never exactly 2,000.
3. **Staleness with no date.** Marketing copy is rarely re-dated when the floor
   changes, so `as_of_date` is the RETRIEVAL date and its precision is
   `observed_on_retrieval_date` — never a count date.

**A number with no verbatim sentence is unusable and is REFUSED at write**, not
downgraded. `source_quote` is asserted non-empty on every row.

### WHY THE EMPLOYMENT LAYER IS THE ONE THAT MATTERS

Measured today against `data/clean/gaming_facility_metrics.csv`:

| `metric = employees` | |
|---|---:|
| rows | **10,122** |
| distinct sources | **1** |
| that source | **Casino City Press gaming-property panel** |
| facilities | 323 |

**100% of Cedar's facility-level employment series is the vendor panel**, which
is QA-reference-only and may never publish. Every row `382` recovers is a
PRIMARY, NON-VENDOR source and is the only per-property employment evidence in
this project that can ship. The yield is 29 rows and that is the point: 29
publishable rows against 10,122 unpublishable ones.

### WHAT IS DELIBERATELY *NOT* A MeasurementType

Dates, ownership statements, management statements, employer-standing claims
and loyalty tiers measure nothing about capacity or employment. They carry an
`assertion_class` and an explicit note saying they sit outside the count
vocabulary — the same decision `142` made for `LABOR_DEMAND_STATEMENT`, for the
same reason: a vocabulary that admits everything stops distinguishing anything.

### THE VOCABULARY WAS REUSED, NOT REINVENTED

`gaming_facility_metrics.metric` already carries ten terms. `142` wrote
`meeting_square_feet`; the metrics table's term is `convention_square_feet`.
**That is a parallel name and it is now mapped, not propagated** —
`PARALLEL_NAME_FIX` renames it and `metric_renamed_from` records the original.
Measures the site corpus carries that the metrics table has no term for
(`venue_capacity`, `hotel_suites`, `rv_spaces`) are kept and flagged
`NEW_MEASURE_no_term_in_gaming_facility_metrics` — never forced into a
neighbouring term.

### THE FOUR RULES HONOURED, AND WHAT EACH COST TO LEARN

**`historical_guard` runs BEFORE anything is extracted for a facility.** Three
gaming rulings were withdrawn 2026-08-06 for ruling properties that closed in
2003–2005 against 2026 pages. The record's own close date is checked first, and
a facility that is `current` AND carries a close date is a **REOPENED property,
not a contradiction** — 115 such rows exist — so it passes. Zero pages were
blocked on this run; the guard is there so the next crawl cannot reintroduce it.

**A management brand is not ownership.** Caesars *manages* Harrah's Cherokee;
EBCI *owns* it. `operated_by` sentences and any known management brand are typed
`SELF_PUBLISHED_MANAGEMENT_ASSERTION`, never ownership. Cedar's curated
`gaming_facilities.csv` outranks every row in the file; `agrees_with_curated_owner`
is a **report** (`SHARES_TOKEN:…`, `NO_SHARED_DISTINCTIVE_TOKEN`,
`CURATED_NAME_IS_A_PREFIX_EXTENSION_OF_ASSERTED`) and never a verdict. Nothing
overwrites, mints or promotes an owner.

**No new facility id is minted.** Asserted per row before write.

**Deterministic keys only (class 7).** Every id is a `sha1` digest of its
identifying fields. `hash()` is never used — Python randomises string hashing
per process, so the same row would get a different id every run.

### FIVE DEFECTS FOUND AND FIXED INSIDE THIS PASS, EACH MEASURED

1. **A soft hyphen split the word the parser needed.** kwataqnuk.com publishes
   `Approxi­mately 300 employees`; the rendered text reads normally and every
   `\bapproximately\b` pattern misses it. Soft hyphens and zero-width joiners
   are now folded — punctuation folding, not identity folding.
2. **`"Live Nation"` resolved as a tribal owner**, because `TRIBAL_FORM` matched
   the word *Nation* inside a concert promoter's name. This is `core()` folding
   `indian` into *National Education Association*, arriving in a third place.
   Fixed with a named `NOT_A_TRIBE` list, not a cleverer regex — **a token that
   makes a name a tribe in one string is a brand in another, and only a person
   can say which.**
3. **A job fair is not a headcount.** Talking Stick Resort: *"will be accepting
   applications for more than 300 positions"*. That is `LABOR_DEMAND_STATEMENT`
   — 142's own vocabulary — and reading it against an employment series would
   have been wrong with a correct citation.
4. **An executive bio counts another company's staff.** Valley View: *"During
   his time at The Resort at Pelican Hill, Maneesh led a team of 350"*. Refused
   as `EXECUTIVE_BIO_ANOTHER_PROPERTY`.
5. **A department is not a property.** KwaTaqNuk's *"300 employees carry out the
   natural resource protection, planning and management"* is a tribal government
   department roster. Refused as `DEPARTMENT_OR_TEAM_SUBSET`. A subset published
   as a property total understates it invisibly.

**`bars_lounges` was built, measured and DELETED.** A number next to "bar" or
"lounge" on this corpus is almost always a venue NAME (*Bar 7* at Coushatta) or
a date in an events strip. Precision too low, yield 2 rows. Recorded here so
nobody rebuilds it.

**The loyalty extractor read the nav bar on its first pass** — producing
programme names like *"Site Catering Careers Rewards Club"* and *"Bar Summer
Sounds Wayfinder Rewards"*, because every nav item is title-cased and adjacent.
It now reads `<title>`, which is the one string on a page the operator wrote as
a NAME, and caps the body fallback at three words. **And the tier row is keyed
on `(host, programme, tier)`, not on the URL** — a ladder is a property of the
programme and a site prints it on every rewards page, so URL keying wrote Seven
Clans Red Lake's ladder **19 times**, which would have read as 19 findings.
182 rows → **65**. That is the correct direction.

**Tier ORDER is not asserted.** Rank is a visual property of the page and is not
recoverable from extracted text, so `tier_rank` is blank with the reason stated.

---

## PHASE 2 — THE 1,621 REFUSALS

`code/383_adjudicate_property_site_refusals.py`. **Zero network requests.**

`142` refused 1,621 numbers rather than dropping them, so recall would be
recoverable. That was right and it is what made this possible. But **every one
of the 1,621 carries the same refusal reason**, which records that one guard
fired and nothing about whether it was right. Same shape as the OCR backlog:
`IMAGE_ONLY_SCAN` fell 264 → 1 when somebody looked properly.

### DOUBLE-COUNTING WAS THE FIRST THING HANDLED

**1,621 rows collapse to 305 distinct `(host, metric, value, sentence)`
candidates.** `142` wrote one row per match OCCURRENCE and a site repeats its
boilerplate across pages. Adjudication runs on the DISTINCT set and both counts
are reported. Claiming 1,621 recoveries off 305 sentences would have been this
project's own additions-glob defect wearing a new hat.

| outcome | distinct | original occurrences |
|---|---:|---:|
| **RECOVERED** | **231** | 1,234 |
| **REFUSAL_CONFIRMED** | 45 | 318 |
| **STILL_AMBIGUOUS** | 29 | 69 |

**231 recovered capacity claims on 49 properties**, staged to
`data/staging/gaming_property_site_recovered_claims_<date>.csv`, typed
`SELF_PUBLISHED_MARKETING_CLAIM` with the verbatim sentence and the bound
direction on every row. **Recovering a number does not upgrade what it is.**

### WHAT 142'S GUARD ACTUALLY MISSED

142 accepts a number only when the immediately preceding WORD is in a 40-item
`CUE_WORDS` set. High precision, and right about the jackpot tickers it was
built for. Wrong about five sentence shapes a casino writes constantly:

| recovery rule | n | the sentence that named it |
|---|---:|---|
| `BOUND_QUALIFIER` | **128** | *"showcases **over** 350 slot machines"* — a qualifier separated from the number by anything at all is invisible to a single-word lookback |
| `SPEC_LIST_AT_CLAUSE_START` | 69 | *"… 2,000 slot machines. **41 table games.**"* |
| `DETERMINER` | 11 | *"With **a** 70,000 square-foot gaming floor"* |
| `MEASURE_CONTEXT_NOUN` | 12 | *"73,000 square feet of **Gaming** 2,000 slot machines"* |
| `ENUMERATION_AFTER_A_CUED_COUNT` | 4 | *"more than 2,000 slot machines, **over 60 table games**"* — the cue governs only the first item |
| `ENUMERATION_BEFORE_A_CUED_COUNT` | 2 | *"**92 table games**, more than 10,000 electronic games"* — the list is one act of enumeration |
| `CLAUSE_START` | 5 | a number opening a clause after a bullet |

### AND THE NEGATIVE GUARDS RUN FIRST AND WIN

A ticker line that also happens to sit after a determiner stays refused. The
one generic reason is replaced by seven named ones:

| confirmed by | n |
|---|---:|
| `JACKPOT_TICKER` | 18 |
| `DOLLAR_AMOUNT` | 13 |
| `GAME_TITLE` | 7 |
| `PROMOTIONAL_OFFER` | 3 |
| `CALENDAR_DATE` | 2 |
| `CALENDAR_YEAR` | 1 |
| `MINIMUM_BOOKING_SIZE` | 1 |

Two of those are new findings, not re-statements of 142's:

- **`CALENDAR_YEAR`.** Augustine Casino's awards strip reads *"BEST OF COACHELLA
  VALLEY 2019-2020 Slot Machines"* and 142 read **2,020 gaming machines** off
  it. A year RANGE escapes every slash-date guard, so it is caught on the VALUE,
  and only for count metrics — 2,000 square feet and 1,995 seats are ordinary
  figures.
- **`MINIMUM_BOOKING_SIZE`.** *"Requires a minimum of 200 guests"* is a floor the
  customer must meet, not a ceiling the venue holds. Inverting one into the
  other is the same error shape as reading a marginal rate as a flat one.

### A BUG IN THE ADJUDICATOR ITSELF, FOUND BY READING ITS OWN OUTPUT

A plain `str.find` located the refused value `200` **inside `5,200`** —
*"construction work began and 5,200 square feet of gaming floor was added"* —
and every context test then read the wrong neighbourhood and recovered a number
that was never there. `locate()` now requires a real numeric boundary. **The
only thing that exposed it was reading thirty recovered rows one at a time.**

---

## PHASE 3 — THE 281 OPEN PROPERTIES NEVER CRAWLED

`code/384_crawl_uncrawled_open_properties.py`. Frame: **280 open properties
with no verified site** (142 said 281; the file today gives 280 — one has since
been matched).

142's generator builds candidates from the PROPERTY NAME only and cannot reach
a property whose domain does not contain its name — *`winstar.com` does not
contain "world"*. This pass widens the candidate set (tribe-name stems, generic
words stripped and re-suffixed, apex as well as `www.`, `.net`/`.org`) and
**imports `verify_host` from 142 unchanged**. The bar is not lowered; only the
number of doors knocked on goes up.

### THE FINDING THAT MADE THE RUN POSSIBLE AT ALL

The first bounded run **stopped itself after 48 requests with zero successes**,
reporting *"the HOST LAYER is refusing"*. It was wrong, and the reason is worth
keeping:

> **A domain that does not resolve is a fact about the OBJECT, not about the
> network.** curl exits `6` (`Couldn't resolve host`) and 142's `fetch` reports
> that as `status 0` — indistinguishable from a dropped connection. The first
> three properties in this frame are Alaska bingo halls whose generated
> candidate domains simply do not exist, so 48 consecutive NXDOMAINs looked
> exactly like an edge block.

`probe()` now returns curl's exit code and types `6` / `51` / `60` as facts
about the object. **Collapsing NXDOMAIN into "transport failure" makes the
block detector useless in exactly the run where it is needed.**

A **DNS pre-filter** was added on the back of it: 71 of the first 80 generated
candidates have no DNS record at all. `resolves()` asks the resolver, which is
not an HTTP request and does not touch the site — and it is the politest
possible ordering, because a name with no record can never be knocked on.

### DISCIPLINE, AS IMPLEMENTED

- one `logs/_HOSTLOCK_<host>.json` per host via 142's own `claim_host` /
  `release_host`, which append to a live peer's queue rather than starting a
  second loop; robots.txt honoured per path; sequential, one request in flight.
- `RUN_DEADLINE` checked before every attempt.
- **Stop on first refusal when nothing has succeeded** — now correctly not
  triggered by NXDOMAIN.
- Failure shapes typed and none read as absence: `TRANSPORT_FAILURE`,
  `NOT_FOUND`, `FORBIDDEN`, **`BOT_WALL_403`** (a 403 whose small body is a
  browser challenge is a fact about the CLIENT), `THROTTLED`, `SERVER_ERROR`.
- **Class 4.** Every property carries `probes_attempted` vs `probes_completed`
  and a `unit_status` that is `INCOMPLETE` whenever they differ. A unit stopped
  on the clock says so in `unit_status_reason` and **is never written `done`**.
- Forbidden hosts inherited from 142 and extended: `api.sam.gov`,
  `api.usaspending.gov`, NIGC and every state gaming regulator. Not contacted.
- **NEAR MISSES go to `review/gaming_domain_near_miss_<date>.csv`** — a host
  that answered, is a gaming site, and names some but not all of the property's
  distinctive tokens. The recall gap stays visible instead of becoming a silent
  zero.

Live pollers observed before starting, per concurrency rule 6:
`121_pull_subawards_api.py` on `api.usaspending.gov` and
`317_cdx_tribal_vendor_hosts.py` on `web.archive.org`. Neither shares a host
with this pass.

---

## WHAT THIS DOES NOT DO

- **Nothing merged into `data/clean/`.** Every output is in `data/staging/` or
  `review/`. `gaming_facility_metrics.csv` has multiple writers and was moving
  today; a merge needs an mtime check and an owner.
- **Casino City was not read, written or published.** No licensed column
  appears in any output.
- **`gaming_property_site_observations.csv` was not touched.** Its 262 rows are
  another build's and they stay exactly as they are. See the latent note below.

### LATENT, RECORDED RATHER THAN PATCHED

`PROPERTY_REPORTED_COUNT` is `is_observed` and is **not** in
`NEVER_PROMOTES_TO_ACTIVE`, so `may_promote(PROPERTY_REPORTED_COUNT,
ACTIVE_FLOOR_COUNT)` returns `True` today. Script 142 writes that type on all
262 rows of `gaming_property_site_observations.csv`, which are marketing
sentences off operator websites — exactly the material the two new types are
barred from promoting.

Nothing promotes anything today, so this is a **latent hole, not a live
defect**, and closing it would change the meaning of a column another build
owns. The correct fix is for 142's rows to be re-typed
`SELF_PUBLISHED_MARKETING_CLAIM` by whoever owns 142, at which point
`PROPERTY_REPORTED_COUNT` can go back to meaning what its name says: a count a
property REPORTED to somebody who asked, on a stated date. The note is in
`cedar_domain.py` beside the sets, not only here.

---

## THE GATE

`293_lint_bug_classes.py` and `62_no_regression_check.py` were run **before**
any file was touched and again after. Both fail, on **six shipping metrics and
one class2c instance that belong to the concurrent lobbying-correction pass
(`code/350`–`358`)**. Named in `AGENTS.md` per standing rule 15, with mtimes,
before this work began; `353` is nine minutes newer than the three earlier
write-ups of the same failure, which is why its class2c instance appears in
this one and not in them.

**This pass creates no new `data/clean/` table**, so none of the five
registration counters can move because of it.

---

## NEXT, IN VALUE ORDER

1. **Rule whether the two new measurement types may enter
   `gaming_facility_metrics.csv`**, and if so merge the 41 + 231 claim rows
   under an mtime check. That table has multiple writers.
2. **Work the 292 date assertions.** 42 already AGREE with Cedar's `open_date`
   year — corroboration for the 415 dates downgraded off fabricated
   day-precision — and the DIFFERS rows are re-sourcing leads with a URL and a
   verbatim sentence each.
3. **Work the 169 ownership assertions** into the certification evidence layer.
   They are non-federal, operator-published, and Cedar's curated file already
   outranks them, so the merge is additive evidence rather than a contest.
4. **The 29 STILL_AMBIGUOUS refusals** need a human eye, not another rule.
5. **Re-run 384 discover to completion** and then `crawl`, then re-run `382`
   over the enlarged manifest.
6. `docs/GAMING_SOURCE_AUDIT_2026-08-26.md` Part 5 item 13 — the codebook
   blocks for the property-site layer are still 6- and 2-variable stubs.
