# Gaming Development & Markets — Phase 1 build log

*Run 2026-08-05. Scripts `code/23a`–`23e`. Console log: `logs/23_gaming_2026-08-05.log`.*
*Plan: `GAMING_DATASET_PLAN.md`. Phase 1 = the decision index + the directory core.*

---

## What was built

| File | Rows | What it is |
|---|---:|---|
| `data/clean/gaming_land_decisions.csv` | 138 | One row per BIA gaming-land decision record |
| `data/clean/gaming_decision_events.csv` | 265 | One row per dated status event behind those records |
| `data/clean/gaming_facilities.csv` | 774 | Directory core — one row per facility |
| `data/clean/gaming_facility_metrics.csv` | 65,223 | One row per quantity **observation** (stage discipline lives here) |
| `data/clean/gaming_decision_compact_join.csv` | 138 | Decision → compact join diagnostic |

Sources archived under `data/raw/external/gaming/` with `_SOURCE_MANIFEST.csv`
(22 rows: 10 fetched from bia.gov with SHA-256 + HTTP status, 12 copied from
votingpatterns/dissertation). Nothing reads outside Cedar Press at runtime.

`entity_id` is blank throughout. Spine linking was out of scope and is not
guessed anywhere.

---

## A. BIA Gaming Land Decisions

**138 records scraped**, matching the count the plan verified. Fetched with
`items_per_page=All` and every facet set to `All` — one server-rendered request,
no pagination walk. `robots.txt` was retrieved in the same run and archived as
fetch-permission evidence; it permits `/as-ia/`.

### Status breakdown (BIA's `Decision Status`, verbatim)

| Status | n |
|---|---:|
| Approved | 104 |
| Disapproved | **29** |
| Pending | 5 |

The companion `/pending` list holds 5 rows; all 5 resolve to Pending rows in the
main index (matched on project-page URL). The Pending view is **worse** than the
main index — its `Tribe(s)` column is blank on all 5 rows — so the main index is
used as the source and `/pending` only as corroboration.

### Legal theory (BIA's literal values, not normalized)

| Legal theory | n |
|---|---:|
| Two-Part Secretarial Determination | 47 |
| Restored Lands | 31 |
| Within or Contiguous to Reservation Boundaries | 25 |
| Oklahoma – Within Former Reservation Boundaries | 17 |
| Initial Reservation | 8 |
| Settlement of a Land Claim | 6 |
| Within Last Recognized Reservation | 3 |
| *(blank — BIA publishes no legal theory for one record)* | 1 |

Note the literal wording differs from the plan's shorthand: BIA writes
**"Two-Part Secretarial Determination"**, not "Two-Part Determination". The
literal value is what is stored.

Disapproval concentrates sharply by theory: Two-Part Secretarial Determination
is 47 records but **19 of the 29 disapprovals** (40% of that theory disapproved),
while every Oklahoma-Within-Former-Reservation and Initial-Reservation record was
approved. That is the proposed-vs-approved gradient the plan wants to study,
visible in the seed table alone.

Coverage: 22 states, 95 distinct tribe strings, decisions dated **1990-03-05 to
2026-03-09** (24 in the 1990s, 40 in the 2000s, 38 in the 2010s, 36 in the 2020s).
**304 document URLs** captured across all 138 rows (every row has at least one),
plus **74 Federal Register URLs**.

### Disapprovals and reversals are data

`decision_status` is a single current-state field and cannot carry a reversal, so
it is **never used alone**. `gaming_decision_events.csv` emits every dated
statement BIA publishes, under four named derivation rules:

| Rule | n | What it reads |
|---|---:|---|
| E1 | 138 | BIA's own Decision Status + Date columns |
| E2 | 74 | Federal Register links — date taken from the URL path, type from the slug's literal leading words |
| E3 | 50 | BIA's free-text note under the `<hr>`, split into paragraphs then semicolon clauses |
| E4 | 3 | Document labels that literally begin `Month D, YYYY - …` |

240 of 265 events carry a date. The 25 undated ones are undated **on purpose** —
see "dates that belong to another record" below.

The three cases the plan named all survive intact:

- **Los Coyotes Barstow** — `Disapproved`, 2008-01-04, Two-Part Secretarial
  Determination, denial letter URL captured.
- **Scotts Valley** — the full arc, as separate dated events on one record:
  approved 2025-01-10 → FR notice 2025-01-15 → **gaming eligibility temporarily
  rescinded effective 2025-03-27** → partial reconsideration 2025-03-28 →
  reconsideration deadline extension 2025-05-20. Plus two *earlier* Scotts Valley
  records (disapproved 2012-05-25, reconsideration disapproved 2013-09-19). BIA
  still lists the 2025 record as "Approved".
- **Koi Nation Shiloh** — approved 2025-01-13, and a Federal Register notice
  published **2026-04-02** whose slug reads `reversal-of-land-acquisition-koi-
  nation-…`. BIA still lists it "Approved". Captured as
  `federal_register_reversal_of_land_acquisition`.

Two records are `Approved` in BIA's status column while carrying a
rescission/reversal event. Any consumer reading only `decision_status` gets both
of them wrong.

### Dates that belong to another record

BIA's notes routinely cite *other* decisions ("See September 19, 2013 Decision";
"Affirming September 18, 2015 decision"). Dating the current row with those would
silently move an event between records. Rule E3 therefore refuses a date when the
clause contains "see" **or** a date immediately followed by "decision". The clause
is still emitted with its verbatim text — only the date is withheld, with the
reason written into `event_date_basis`. Two such dates were withdrawn by this rule.
Bare years ("The Department approved the application in 2011") are never promoted
to dates.

### New source defect found: the BIA Tribe(s) column is misaligned here too

`STATE_OF_BUILD.md` records that the BIA **compact** index misaligns its `Tribes`
column with its `Title` column on 61 of 1,189 rows. The same check was run on the
**decisions** index and it fires on **3 of 138 rows (2.2%)**:

| decision_id | BIA `Tribe(s)` column | BIA title & documents actually say |
|---|---|---|
| `GLD-CA-ewiiaapaayp-band-of-kumeyaay-indians-cal-20080418` | Ewiiaapaayp Band of Kumeyaay Indians, California | Federated Indians of Graton Rancheria |
| `GLD-LA-tonawanda-band-of-seneca-19931115` | Tonawanda Band of Seneca *(filed under Louisiana)* | Tunica-Biloxi Indian Tribe, Avoyelles Parish |
| `GLD-NY-rappahannock-tribe-inc-20080104` | Rappahannock Tribe, Inc. | Saint Regis Mohawk Tribe, Monticello Parcel |

BIA's value is **preserved verbatim** and never overwritten. The rows carry
`bia_tribes_column_conflict=1` and a `tribe_from_title` candidate corroborated
against the linked document labels. This is the same defect class as the compact
index and it should be assumed present in any other extraction of this page.

### Not done in this phase (by instruction)

No NEPA EA/EIS document was downloaded or parsed. Only URLs were recorded. The
five Pending rows list no documents in the index, so their five individual BIA
**project pages** were fetched — those are document-listing pages, not NEPA
documents — yielding 32 further document URLs (including the Osage Lake Ozark EA
and the Menominee Kenosha EA appendix set that Phase 2 will pilot on).

---

## B. Directory core — honest source assessment

Twelve files were copied in from votingpatterns and the dissertation project
(both read-only; nothing was written back). Assessment before use:

| Source | Rows | What the numbers actually are |
|---|---:|---|
| `tribal_casino_panel.dta` (Casino City Press) | 13,198 obs / 440 properties / 43 waves 2001-09→2023-01 | **REPORTED** capacity: slots, casino sq ft, table games, rooms, employees, parking. **No revenue column at all.** Integer `0` stands in for missing — read as unknown, never as "zero slots". |
| `Tribal Property List.xlsx` | 612 | **REPORTED**. Supplies the Casino City ID join key and open/close dates. No capacity, no revenue. |
| `Indian Gaming Dataset.xlsx` (Sheet1) | 222 | **REPORTED**, and the best-documented provenance here: every opening/closing event carries its own source URL and a "last reviewed" date. |
| `canonical_casino_addresses_FINAL/_supplement.csv` | 411 | **REPORTED** identity/address/coordinates — but ~93% of provenance is the casino's own marketing website, not a regulator. Self-collected, unaudited. `zip`/`county_fips` stored as integers, leading zeros already destroyed at source. |
| `bia_compact_properties_geocoded_v2.csv` | 766 | Text extraction is reported; the **geocoding is mostly absent** — `geocoder_match_quality=No_Match` on 590 of 766, and `pairing_uncertain=1` on 231. Not used as a facility spine. |
| `per_property_gaming_revenue_FINAL_v3_audited.csv` | 512 | **Mostly NOT reported.** See below. |
| `published_tribal_gaming_revenue_v3_audited.csv` | 530 | `value_usd_millions` is a **payment or fee**, not gaming revenue (except CT slot win). 442 rows source-archived; **83 are hand-written estimates with `data_archived_at='not_archived'`**. |
| `per_tribe_gaming_revenue_reverse_engineered.csv` | 611 | Payments, plus implied GGR on only 17 rows. Its `method` column conflates derivation with a *join failure* — `no_aiannh_match` (239 rows) is a crosswalk miss, not a value basis. Not used as a basis source. |

### The trap in the revenue file, and how it was avoided

`per_property_gaming_revenue_FINAL_v3_audited.csv` labels **435 of its 512 rows
`tier2A_agent_verified_real`**. That label certifies the *payment* was verified
against an archived source document. It does **not** mean revenue was reported —
**372 of those 435 rows are compact-rate inversions** (OK ×20, CT ×4). The v2
vintage labeled them honestly as `tier2b_reverse_engineered`; the "audited"
label overwrote that.

Cedar Press therefore derives `value_basis` **from the metric**, never from that
tier. The rates come from the source project's own README, verbatim ("OK
exclusivity fees / 0.05", "CT slot contributions / 0.25"), and each was
re-confirmed against the exact multiplier observed between the payment file and
the implied-GGR file.

### `value_basis` vocabulary, applied to every numeric field

| value_basis | Meaning |
|---|---|
| `reported` | The source publishes this exact quantity |
| `payments_derived` | Revenue obtained by inverting a compact rate on a payment that **is** source-archived (OK /0.05, CT /0.25) |
| `reverse_engineered` | Revenue obtained by inverting a rate on a payment that is **hand-written and unverified** (MI, OR, NY, WA, WI, OK compact share) |
| `modelled` | IMPLAN output, or a direct estimate (MIGA self-reported; Seminole Hollywood/Tampa industry estimates) |

### Reported vs derived — the count

**65,223 observations in `gaming_facility_metrics.csv`:**

| value_basis | n |
|---|---:|
| `reported` | 64,691 |
| `payments_derived` | 372 |
| `modelled` | 122 |
| `reverse_engineered` | 38 |

**Of the 1,042 dollar observations only:**

| measure_type | value_basis | n |
|---|---|---:|
| gaming_revenue | `reported` | **126** |
| gaming_revenue | `payments_derived` | 372 |
| gaming_revenue | `modelled` | 56 |
| gaming_revenue | `reverse_engineered` | 38 |
| payment_to_government | `reported` | 384 |
| payment_to_government | `modelled` | 66 |

**Only 126 of 592 gaming-revenue observations (21.3%) are reported revenue** —
essentially Connecticut slot win. 466 are derived, and the file says so on every
row. Coverage: 112 tribes, fiscal years 1994–2026.

Arizona is carried **state-aggregate only**. AZ compacts prohibit per-tribe
disclosure; the source project's own audit report documents that 19 per-tribe AZ
rows in an earlier vintage were produced by proportionally guessing a statewide
total and were removed. They are not reintroduced here.

**No dollar figure appears on a facility row.** The revenue panel's
"property_name" matches a named casino for only 3 of 512 rows — its "properties"
are overwhelmingly tribes. Revenue therefore lives at `entity_level='tribe'` in
the metrics file, and a facility row never claims revenue it cannot support.

### Stage discipline

Every observation carries `observation_status` ∈ {proposed, approved, built,
current} plus the literal source status:

| measure_type | observation_status | n |
|---|---|---:|
| capacity | current | 63,073 |
| capacity | **proposed** | 717 |
| capacity | **approved** | 391 |
| gaming_revenue | current | 592 |
| payment_to_government | current | 450 |

**1,108 capacity observations across 70 facilities are proposal- or
construction-stage** (Casino City `Planned` / `Under Construction`), including
298 machine counts and 212 gaming-square-footage figures. These are exactly the
numbers that get quoted as facility facts elsewhere. Mapping: `Planned` →
`proposed`, `Under Construction` → `approved`, `Open`/`Temporarily Closed` →
`current`; the literal Casino City value travels in `source_status_literal` on
every row so the mapping can be audited or overridden.

### Facility spine and matching

**774 facilities**, 31 states, 317 distinct tribe strings, 688 with coordinates,
559 with an opening date (112 of those carrying a per-event source URL).

| match_status | n |
|---|---:|
| `casino_city_only` | 369 |
| `matched_casino_city_and_votingpatterns` | 241 |
| `votingpatterns_only_no_exact_casino_city_match` | 164 |

Matching is **exact on normalized (name, state)**, with a second exact pass on
normalized (street address, state) — 3 matches came from the address key. No
fuzzy or token-subset matching was performed; per the project rule, a missed link
is recoverable and a false one is not.

**The 164 unmatched votingpatterns rows all carry `duplicate_risk=1`.** 94 of
them belong to a tribe that already appears in Casino City, so 164 is an *upper
bound* on genuinely new facilities, not a count of them. Resolving them is a
rulings job, not a scraper job.

A build defect was caught and fixed mid-run: pandas `itertuples` mangles column
names containing spaces into positional `_0`/`_1` fields, which silently dropped
**every** date from the Tribal Property List on the first pass. The join now
reads dict records and asserts its expected columns are present.

---

## C. Join to the compact layer

`gaming_land_decisions.csv` (138) → `compacts.csv` (707) on tribe name + state,
at four declared strictness levels. Nothing is forced; non-matches stay blank.

| Level | n |
|---|---:|
| L1 exact normalized (tribe, state) | 117 |
| L2 exact normalized tribe, any state | 4 |
| L3 distinctive-token-**set equality** within state | 1 |
| L4 retry via `tribe_from_title` on a BIA-column-conflicted row | 3 |
| no match | 13 |

**Join rate: 125 of 138 (90.6%)**, touching 175 of the 707 compacts.

By status: Approved 99/104 (95.2%), Disapproved 22/29 (75.9%), Pending 4/5 (80%).
The gradient is meaningful, not a defect — a tribe whose gaming-land application
was denied often has no Class III compact, so a non-match is frequently the true
answer rather than a join failure.

L3 requires token-set **equality**, not overlap. Overlap produces the "Pueblo of
Santa Ana" / "Pueblo of Santa Clara" class of false match and is not used.

10 decisions match a compact whose own `bia_tribes_column_conflict` flag is set —
i.e. the join runs through a row the compact build already flagged as
BIA-misaligned. Flagged in the output, not silently trusted.

The 9 remaining unmatched tribe-state pairs: Cloverdale Rancheria, Guidiville
Rancheria, Koi Nation, Los Coyotes, Lytton Rancheria, Scotts Valley (all CA),
Miami Tribe of Oklahoma (a decision sited in **Indiana**, so a state-scoped join
correctly declines it), Santee Sioux Nation (NE), Cayuga Nation (NY).

---

## Coverage caveats — publish these

**1. Structural bias: the decision layer only sees projects that needed a federal
action.** Fee-to-trust acquisitions, gaming-eligibility determinations and
off-reservation projects trigger federal review, and review is what generates
this paper trail. **Routine on-reservation construction on land already in trust
never enters this pipeline.** The 138 records therefore over-represent
fee-to-trust, off-reservation, newly-acquired-land and contested projects, and
say nothing about the much larger volume of ordinary on-reservation building. The
directory core carries the broad facility universe; the decision layer is deep
only where federal review reached.

**2. BIA states its own list is not exhaustive.** It is the seed table, not the
census. Regional office pages and a Federal Register sweep will net additional
projects.

**3. Proposed ≠ built.** 1,108 capacity observations in this build are proposal-
or construction-stage. Never quote one as a facility fact. `observation_status`
is on every row for exactly this reason.

**4. Only 21% of gaming-revenue observations are reported revenue.** The rest are
rate inversions of state payments or model output. Indian gaming does not
disclose revenue; nothing here changes that. Read `value_basis` before quoting
any dollar figure.

**5. Directory coverage is a union of imperfect rosters, not a census.** Casino
City's panel ends 2023-01 and its capacity fields are sparse (table games 41%,
hotel rooms 22% of property-waves). 164 facility rows carry `duplicate_risk=1`.
The address layer's provenance is overwhelmingly operator marketing websites.

**6. Two BIA source defects are carried, flagged, into this build**: the
Tribe(s)-column misalignment on the decisions index (3 of 138) and the same
defect on the compact index (61 of 1,189, per `STATE_OF_BUILD.md`). Neither was
corrected in place; both are flagged with the evidence needed to adjudicate them.

---

## Next (Phase 2, per the plan)

Extraction pilot on the Osage Lake Ozark EA (clean single document), then
Menominee Kenosha (stress test — 19 documents including 16 separately-posted
appendices, all URLs already captured here). That needs the three-table extraction schema and the
reported/calculated discipline validated before any bulk run.
